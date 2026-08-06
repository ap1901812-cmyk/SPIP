from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.db.models.domain import Material, PlanningExecutionRecord, Plant, PlantMaterial
from app.services.data_intelligence.quality_scanner import DataQualityScanner
from app.services.forecasting.engine import generate_demand_forecast
from app.services.planning.consumption_intelligence import analyze_consumption_intelligence
from app.services.planning.dependency_intelligence import get_fg_dependency_matrix
from app.services.planning.inventory_intelligence import analyze_inventory_intelligence
from app.services.planning.lead_time import resolve_dual_lead_time
from app.services.planning.pm_planning import evaluate_pm_planning
from app.services.planning.production_readiness import evaluate_fg_production_readiness
from app.services.planning.readiness import PlanningReadinessEngine
from app.services.planning.requirement_resolution import resolve_planning_requirement
from app.services.planning.rm_totality import build_and_evaluate_rm_totality
from app.services.planning.safety_stock import calculate_dual_safety_stock


class PipelineExecutionMetadata(BaseModel):
    start_time: datetime
    end_time: datetime
    duration_ms: float
    status: Literal["SUCCESS", "BLOCKED", "FAILED"]
    modules_executed: list[str] = Field(default_factory=list)
    modules_skipped: list[str] = Field(default_factory=list)
    failure_reason: str | None = None


class UnifiedPlanningResult(BaseModel):
    plant_code: str
    material_code: str | None = None
    material_type: str | None = None
    as_of_timestamp: datetime
    execution_metadata: PipelineExecutionMetadata
    intermediate_results: dict[str, Any] = Field(default_factory=dict)
    unified_planning_summary: dict[str, Any] = Field(default_factory=dict)


def execute_full_planning_pipeline(
    db: Session,
    plant_code: str,
    material_code: str,
    horizon_days: int = 30,
    user_id: int | None = None,
) -> UnifiedPlanningResult:
    """Central Planning Orchestrator executing the 11-step SPIP V2 planning pipeline in strict dependency order:

    Enterprise Data Intelligence -> Planning Readiness -> Consumption Intelligence ->
    Inventory Intelligence -> RMPM Statistical Planning -> Forecasting ->
    Requirement Resolution -> RM Totality Planning -> PM Planning ->
    Dependency Intelligence -> Production Readiness -> Unified Planning Result.
    """
    start_ts = datetime.now(UTC)
    t0 = time.perf_counter()

    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise ValueError(f"Plant '{plant_code}' not found.")

    material = None
    if material_code:
        material = db.query(Material).filter(Material.code == material_code).first()
        if not material:
            raise ValueError(f"Material '{material_code}' not found.")
    else:
        pm = db.query(PlantMaterial).filter(PlantMaterial.plant_id == plant.id).first()
        if pm:
            material = pm.material
        else:
            material = db.query(Material).first()

    mat_id = material.id if material else 1
    mat_code = material.code if material else "ALL"
    mat_type = material.material_type if material else "RM"

    modules_executed: list[str] = []
    modules_skipped: list[str] = []
    results: dict[str, Any] = {}
    failure_reason: str | None = None
    execution_status: Literal["SUCCESS", "BLOCKED", "FAILED"] = "SUCCESS"

    all_modules = [
        "ENTERPRISE_DATA_INTELLIGENCE",
        "PLANNING_READINESS",
        "CONSUMPTION_INTELLIGENCE",
        "INVENTORY_INTELLIGENCE",
        "RMPM_STATISTICAL_PLANNING",
        "FORECASTING",
        "REQUIREMENT_RESOLUTION",
        "RM_TOTALITY_PLANNING",
        "PM_PLANNING",
        "DEPENDENCY_INTELLIGENCE",
        "PRODUCTION_READINESS",
    ]

    try:
        # Step 1: Enterprise Data Intelligence
        scanner = DataQualityScanner()
        results["enterprise_data_intelligence"] = scanner.summary.model_dump()
        modules_executed.append("ENTERPRISE_DATA_INTELLIGENCE")

        # Step 2: Planning Readiness (Gating Step)
        readiness_engine = PlanningReadinessEngine(db, user_id=user_id)
        readiness_res = readiness_engine.evaluate_readiness(plant_code)
        results["planning_readiness"] = readiness_res.model_dump()
        modules_executed.append("PLANNING_READINESS")

        if readiness_res.readiness_state.value == "BLOCKED" or not readiness_res.can_proceed_to_planning:
            execution_status = "BLOCKED"
            failure_reason = f"Pipeline blocked by Planning Readiness score ({readiness_res.score:.1f}%)."
            modules_skipped = [m for m in all_modules if m not in modules_executed]

        elif material:
            # Step 3: Consumption Intelligence
            c_intel = analyze_consumption_intelligence(db, plant.id, material.id)
            results["consumption_intelligence"] = c_intel.model_dump()
            modules_executed.append("CONSUMPTION_INTELLIGENCE")

            # Step 4: Inventory Intelligence
            inv_intel = analyze_inventory_intelligence(db, plant.id, material.id)
            results["inventory_intelligence"] = inv_intel.model_dump()
            modules_executed.append("INVENTORY_INTELLIGENCE")

            # Step 5: RMPM Statistical Planning
            lt_res = resolve_dual_lead_time(db, plant.id, material.id)
            pm = db.query(PlantMaterial).filter(PlantMaterial.plant_id == plant.id, PlantMaterial.material_id == material.id).first()
            ss_res = calculate_dual_safety_stock(
                c_intel.demand_std_dev, lt_res.lead_time_1, lt_res.lead_time_2, plant_material=pm
            )
            trigger_1 = round(inv_intel.planning_available_inventory - (c_intel.average_daily_demand * lt_res.lead_time_1) - ss_res.safety_stock_1, 2)
            trigger_2 = round(inv_intel.planning_available_inventory - (c_intel.average_daily_demand * lt_res.lead_time_2) - ss_res.safety_stock_2, 2)

            rmpm_out = {
                "lead_time_1": lt_res.lead_time_1,
                "lead_time_2": lt_res.lead_time_2,
                "safety_stock_1": ss_res.safety_stock_1,
                "safety_stock_2": ss_res.safety_stock_2,
                "trigger_1": trigger_1,
                "trigger_2": trigger_2,
            }
            results["rmpm_statistical_planning"] = rmpm_out
            modules_executed.append("RMPM_STATISTICAL_PLANNING")

            # Step 6: Forecasting
            try:
                fc_res = generate_demand_forecast(db, plant_code, mat_code, horizon_days=horizon_days)
                fc_daily = fc_res.average_forecasted_daily_demand
                results["forecasting"] = fc_res.model_dump()
            except Exception:
                fc_daily = 0.0
                results["forecasting"] = {"average_forecasted_daily_demand": 0.0}
            modules_executed.append("FORECASTING")

            # Step 7: Requirement Resolution
            req_res = resolve_planning_requirement(
                db,
                plant_id=plant.id,
                material_id=material.id,
                forecast_daily_qty=fc_daily,
                historical_daily_qty=c_intel.average_daily_demand,
            )
            results["requirement_resolution"] = req_res.model_dump()
            modules_executed.append("REQUIREMENT_RESOLUTION")

            # Step 8: RM Totality Planning (if RM)
            if material.material_type == "RM":
                rm_res = build_and_evaluate_rm_totality(db, plant.id, material.id, req_res.final_planning_requirement)
                results["rm_planning"] = rm_res.model_dump()
                modules_executed.append("RM_TOTALITY_PLANNING")
            else:
                modules_skipped.append("RM_TOTALITY_PLANNING")

            # Step 9: PM Planning (if PM)
            if material.material_type == "PM":
                pm_res = evaluate_pm_planning(db, plant.id, material.id, material.id, req_res.final_planning_requirement)
                results["pm_planning"] = pm_res.model_dump()
                modules_executed.append("PM_PLANNING")
            else:
                modules_skipped.append("PM_PLANNING")

            # Step 10: Dependency Intelligence (if FG)
            if material.material_type == "FG":
                dep_matrix = get_fg_dependency_matrix(db, plant.id, material.id)
                results["dependency_summary"] = dep_matrix.model_dump()
                modules_executed.append("DEPENDENCY_INTELLIGENCE")

                # Step 11: Production Readiness (if FG)
                pr_res = evaluate_fg_production_readiness(db, plant_code, material_code, user_id=user_id)
                results["production_readiness"] = pr_res.model_dump()
                modules_executed.append("PRODUCTION_READINESS")
            else:
                modules_skipped.append("DEPENDENCY_INTELLIGENCE")
                modules_skipped.append("PRODUCTION_READINESS")

    except Exception as exc:
        execution_status = "FAILED"
        failure_reason = str(exc)
        modules_skipped = [m for m in all_modules if m not in modules_executed]

    t1 = time.perf_counter()
    duration_ms = round((t1 - t0) * 1000.0, 2)
    end_ts = datetime.now(UTC)

    metadata = PipelineExecutionMetadata(
        start_time=start_ts,
        end_time=end_ts,
        duration_ms=duration_ms,
        status=execution_status,
        modules_executed=modules_executed,
        modules_skipped=modules_skipped,
        failure_reason=failure_reason,
    )

    # Consolidated Unified Planning Summary
    summary = {
        "final_planning_requirement": results.get("requirement_resolution", {}).get("final_planning_requirement", 0.0),
        "requirement_source": results.get("requirement_resolution", {}).get("requirement_source", "HISTORICAL_CONSUMPTION"),
        "production_readiness_status": results.get("production_readiness", {}).get("status", "N/A"),
        "overall_status": execution_status,
    }

    # Save PlanningExecutionRecord in DB if material exists
    if material:
        exec_rec = PlanningExecutionRecord(
            plant_id=plant.id,
            material_id=material.id,
            execution_status=execution_status,
            duration_ms=duration_ms,
            modules_executed_json=json.dumps(modules_executed),
            modules_skipped_json=json.dumps(modules_skipped),
            failure_reason=failure_reason,
            details_json=json.dumps(summary),
        )
        db.add(exec_rec)
        db.flush()

    # Log audit event
    record_audit_event(
        db,
        user_id=user_id,
        action="EXECUTE_PLANNING_PIPELINE",
        resource_type="PlanningExecutionRecord",
        resource_id=str(exec_rec.id) if 'exec_rec' in locals() and exec_rec else "PIPELINE",
        details={
            "plant_code": plant_code,
            "material_code": material_code,
            "status": execution_status,
            "duration_ms": duration_ms,
        },
    )

    return UnifiedPlanningResult(
        plant_code=plant_code,
        material_code=material_code or (material.code if material else None),
        material_type=material.material_type if material else "RM",
        as_of_timestamp=end_ts,
        execution_metadata=metadata,
        intermediate_results=results,
        unified_planning_summary=summary,
    )


def get_planning_execution_history(
    db: Session,
    plant_code: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve planning pipeline execution logs."""
    query = db.query(PlanningExecutionRecord)
    if plant_code:
        plant = db.query(Plant).filter(Plant.code == plant_code).first()
        if plant:
            query = query.filter(PlanningExecutionRecord.plant_id == plant.id)

    recs = query.order_by(PlanningExecutionRecord.executed_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "plant_code": r.plant.code if r.plant else None,
            "material_code": r.material.code if r.material else None,
            "execution_status": r.execution_status,
            "duration_ms": r.duration_ms,
            "executed_at": r.executed_at.isoformat(),
            "failure_reason": r.failure_reason,
        }
        for r in recs
    ]


def get_planning_execution_details(
    db: Session,
    execution_id: int,
) -> dict[str, Any] | None:
    """Retrieve full details for a single planning pipeline execution."""
    rec = db.query(PlanningExecutionRecord).filter(PlanningExecutionRecord.id == execution_id).first()
    if not rec:
        return None

    return {
        "id": rec.id,
        "plant_code": rec.plant.code if rec.plant else None,
        "material_code": rec.material.code if rec.material else None,
        "execution_status": rec.execution_status,
        "duration_ms": rec.duration_ms,
        "modules_executed": json.loads(rec.modules_executed_json),
        "modules_skipped": json.loads(rec.modules_skipped_json),
        "failure_reason": rec.failure_reason,
        "details": json.loads(rec.details_json) if rec.details_json else {},
        "executed_at": rec.executed_at.isoformat(),
    }
