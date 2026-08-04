from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import (
    Allocation,
    Material,
    Plant,
    ProcurementRecommendation,
    ProductionReadinessRecord,
)
from app.services.planning.orchestrator import execute_full_planning_pipeline


class DecisionSupportSummary(BaseModel):
    plant_code: str
    material_code: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    planning_summary: dict[str, Any]
    procurement_summary: dict[str, Any]
    production_summary: dict[str, Any]
    inventory_summary: dict[str, Any]
    recommendation_summary: list[dict[str, Any]] = Field(default_factory=list)


def get_decision_support_summary(
    db: Session, plant_code: str, material_code: str | None = None
) -> DecisionSupportSummary:
    """Collects outputs from all planning modules and provides planners with a consolidated decision explanation."""
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise AppError("PLANT_NOT_FOUND", f"Plant with code '{plant_code}' not found.", 404)

    # Consume Central Planning Orchestrator outputs
    pipeline_res = execute_full_planning_pipeline(
        db=db, plant_code=plant_code, material_code=material_code, horizon_days=15
    )

    inter_results = pipeline_res.intermediate_results

    # 1. Planning Summary
    readiness_data = inter_results.get("planning_readiness", {})
    readiness_score = readiness_data.get("score", 100.0)
    readiness_state = readiness_data.get("readiness_state", "READY")

    planning_summary = {
        "as_of_timestamp": datetime.utcnow().isoformat(),
        "readiness_score": readiness_score,
        "readiness_state": readiness_state,
        "pipeline_execution_status": pipeline_res.execution_metadata.status,
        "duration_ms": pipeline_res.execution_metadata.duration_ms,
        "modules_executed": pipeline_res.execution_metadata.modules_executed,
    }

    # 2. Procurement Summary
    recs_query = db.query(ProcurementRecommendation).filter(
        ProcurementRecommendation.plant_id == plant.id
    )
    if material_code:
        mat = db.query(Material).filter(Material.code == material_code).first()
        if mat:
            recs_query = recs_query.filter(ProcurementRecommendation.material_id == mat.id)

    all_recs = recs_query.all()
    critical_count = sum(1 for r in all_recs if r.priority == "CRITICAL")
    high_count = sum(1 for r in all_recs if r.priority == "HIGH")

    allocs_query = db.query(Allocation).filter(Allocation.plant_id == plant.id)
    if material_code and mat:
        allocs_query = allocs_query.filter(Allocation.material_id == mat.id)

    total_allocated_qty = sum(a.allocated_quantity for a in allocs_query.all())

    procurement_summary = {
        "total_recommendations_count": len(all_recs),
        "critical_priority_count": critical_count,
        "high_priority_count": high_count,
        "total_allocated_quantity": round(total_allocated_qty, 2),
        "active_procurement_mode": "PROACTIVE",
    }

    # 3. Production Summary
    prod_records = (
        db.query(ProductionReadinessRecord)
        .filter(ProductionReadinessRecord.plant_id == plant.id)
        .all()
    )
    ready_count = sum(1 for p in prod_records if p.status == "READY_TO_PRODUCE")
    blocked_count = sum(1 for p in prod_records if p.status == "BLOCKED")
    total_fg = len(prod_records)
    readiness_pct = (ready_count / total_fg * 100.0) if total_fg > 0 else 100.0

    production_summary = {
        "total_evaluated_fg_count": total_fg,
        "ready_to_produce_fg_count": ready_count,
        "blocked_fg_count": blocked_count,
        "production_readiness_percentage": round(readiness_pct, 1),
    }

    # 4. Inventory Summary
    inv_data = inter_results.get("inventory_intelligence", {})
    usable_stock = inv_data.get("usable_physical_stock", 0.0)
    incoming_po = inv_data.get("incoming_po_quantity", 0.0)
    available_stock = inv_data.get("planning_available_inventory", usable_stock + incoming_po)

    c_data = inter_results.get("consumption_intelligence", {})
    daily_demand = c_data.get("average_daily_demand", 0.0)
    doi = (available_stock / daily_demand) if daily_demand > 0 else 999.0

    inventory_summary = {
        "usable_physical_stock": round(usable_stock, 2),
        "incoming_po_quantity": round(incoming_po, 2),
        "planning_available_inventory": round(available_stock, 2),
        "average_daily_demand": round(daily_demand, 2),
        "days_of_inventory": round(doi, 1),
    }

    # 5. Recommendation Summary
    recommendation_summary = []
    for r in all_recs[:5]:
        recommendation_summary.append(
            {
                "id": r.id,
                "material_code": r.material.code if r.material else "",
                "recommended_qty": r.recommended_qty,
                "priority": r.priority,
                "planning_mode": r.planning_mode,
                "status": r.status,
                "reason": r.reason,
            }
        )

    return DecisionSupportSummary(
        plant_code=plant.code,
        material_code=material_code,
        planning_summary=planning_summary,
        procurement_summary=procurement_summary,
        production_summary=production_summary,
        inventory_summary=inventory_summary,
        recommendation_summary=recommendation_summary,
    )
