from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import Material, Plant, PlantMaterial
from app.services.planning.orchestrator import execute_full_planning_pipeline


class ExplainabilityReport(BaseModel):
    plant_code: str
    material_code: str
    material_description: str
    material_type: str
    source_data_used: list[dict[str, str]] = Field(default_factory=list)
    planning_modules_involved: list[str] = Field(default_factory=list)
    business_rules_applied: list[str] = Field(default_factory=list)
    constraints_applied: dict[str, Any] = Field(default_factory=dict)
    intermediate_calculations: dict[str, Any] = Field(default_factory=dict)
    final_recommendation: dict[str, Any] = Field(default_factory=dict)
    confidence_indicators: dict[str, Any] = Field(default_factory=dict)


def get_explainability_report(
    db: Session, plant_code: str, material_code: str
) -> ExplainabilityReport:
    """Provides transparent explainability for planning results without recalculating business logic."""
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise AppError("PLANT_NOT_FOUND", f"Plant with code '{plant_code}' not found.", 404)

    mat = db.query(Material).filter(Material.code == material_code).first()
    if not mat:
        raise AppError("MATERIAL_NOT_FOUND", f"Material with code '{material_code}' not found.", 404)

    pm = (
        db.query(PlantMaterial)
        .filter(PlantMaterial.plant_id == plant.id, PlantMaterial.material_id == mat.id)
        .first()
    )

    # Consume Central Planning Orchestrator outputs
    pipeline_res = execute_full_planning_pipeline(
        db=db, plant_code=plant_code, material_code=material_code, horizon_days=15
    )

    results = pipeline_res.intermediate_results

    # 1. Source Data Used
    source_data_used = [
        {"entity": "InventorySnapshot", "source": "SAP_MB5B", "description": "Physical usable & unrestricted stock"},
        {"entity": "ConsumptionHistory", "source": "SAP_MB51", "description": "Historical issue goods movement records"},
        {"entity": "PlantMaterial", "source": "Master Maintenance", "description": "Lead times, Service level Z, Review period"},
        {"entity": "RMTotalityMapping", "source": "Totality Engine", "description": "Raw material finished goods family mapping"},
    ]

    # 2. Planning Modules Involved
    planning_modules_involved = pipeline_res.execution_metadata.modules_executed

    # 3. Business Rules Applied
    business_rules_applied = [
        "RMPM Statistical Planning: Dual Lead Time (LT-1 normal supplier, LT-2 express/emergency)",
        "Safety Stock Calculation: SS-1 = Z * Demand_StdDev * sqrt(LT-1), SS-2 = Z * Demand_StdDev * sqrt(LT-2)",
        "Trigger Level Rules: Trigger-1 = NetAvailable - (D_avg * LT-1) - SS-1",
        "Requirement Resolution Hierarchy: IBP Demand -> Monthly Schedule / 22 -> Statistical Forecast -> Historical Average",
        "RM Dependency: Totality Mapping used exclusively for Raw Materials (BOM overridden)",
    ]

    # 4. Constraints Applied
    c_intel = results.get("consumption_intelligence", {})
    inv_intel = results.get("inventory_intelligence", {})
    rmpm = results.get("rmpm_statistical_planning", {})
    req_res = results.get("requirement_resolution", {})

    constraints_applied = {
        "storage_capacity_limit": mat.storage_capacity_limit or "Unlimited",
        "minimum_order_quantity": pm.reorder_point if pm else 0.0,
        "lead_time_1_days": rmpm.get("lead_time_1", pm.lead_time_1 if pm else 7.0),
        "lead_time_2_days": rmpm.get("lead_time_2", pm.lead_time_2 if pm else 3.0),
        "safety_stock_1_target": rmpm.get("safety_stock_1", 0.0),
        "safety_stock_2_target": rmpm.get("safety_stock_2", 0.0),
    }

    # 5. Intermediate Calculations
    intermediate_calculations = {
        "average_daily_demand": c_intel.get("average_daily_demand", 0.0),
        "demand_std_dev": c_intel.get("demand_std_dev", 0.0),
        "usable_physical_stock": inv_intel.get("usable_physical_stock", 0.0),
        "incoming_po_quantity": inv_intel.get("incoming_po_quantity", 0.0),
        "planning_available_inventory": inv_intel.get("planning_available_inventory", 0.0),
        "final_planning_requirement": req_res.get("final_planning_requirement", 0.0),
        "resolution_source": req_res.get("requirement_source", "HISTORICAL_AVERAGE"),
        "trigger_1": rmpm.get("trigger_1", 0.0),
        "trigger_2": rmpm.get("trigger_2", 0.0),
    }

    # 6. Final Recommendation Summary
    avail = inv_intel.get("planning_available_inventory", 0.0)
    ss1 = rmpm.get("safety_stock_1", 0.0)
    trig1 = rmpm.get("trigger_1", 0.0)

    if avail <= ss1:
        rec_priority = "CRITICAL"
        rec_reason = f"Available inventory ({avail:.1f}) is at or below Safety Stock 1 target ({ss1:.1f})."
    elif avail <= trig1:
        rec_priority = "HIGH"
        rec_reason = f"Available inventory ({avail:.1f}) breached Trigger 1 threshold ({trig1:.1f})."
    else:
        rec_priority = "MEDIUM"
        rec_reason = "Rolling horizon planning requirement."

    final_recommendation = {
        "material_code": mat.code,
        "priority": rec_priority,
        "reason": rec_reason,
        "suggested_procurement_action": "REORDER" if avail <= trig1 else "MONITOR",
    }

    # 7. Confidence Indicators
    readiness_score = results.get("planning_readiness", {}).get("score", 100.0)
    fc_data = results.get("forecasting", {})
    wmape = fc_data.get("wmape_score", 0.15)
    forecast_conf = max(0.0, min(1.0, 1.0 - wmape)) if wmape is not None else 0.85

    confidence_indicators = {
        "readiness_score": readiness_score,
        "forecast_confidence_score": round(forecast_conf, 2),
        "data_quality_status": "CLEAN" if readiness_score >= 80.0 else "WARNING",
    }

    return ExplainabilityReport(
        plant_code=plant.code,
        material_code=mat.code,
        material_description=mat.description,
        material_type=mat.material_type,
        source_data_used=source_data_used,
        planning_modules_involved=planning_modules_involved,
        business_rules_applied=business_rules_applied,
        constraints_applied=constraints_applied,
        intermediate_calculations=intermediate_calculations,
        final_recommendation=final_recommendation,
        confidence_indicators=confidence_indicators,
    )
