from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.db.models.domain import Material, Plant, ProductionReadinessRecord
from app.services.planning.dependency_intelligence import get_fg_dependency_matrix
from app.services.planning.engine import evaluate_material_planning

ProductionReadinessStatusEnum = Literal[
    "READY_TO_PRODUCE",
    "RM_SHORTAGE",
    "PM_SHORTAGE",
    "PRODUCTION_BLOCKED",
]


class BlockingMaterialDetail(BaseModel):
    material_code: str
    material_description: str
    material_type: str  # RM or PM
    planning_available_stock: float
    trigger_2: float
    rmpm_status: str
    reason: str


class ImpactedFGDetail(BaseModel):
    fg_code: str
    fg_description: str
    affected_by_rm: bool
    affected_by_pm: bool


class ProductionReadinessResult(BaseModel):
    plant_code: str
    fg_code: str
    fg_description: str
    status: ProductionReadinessStatusEnum
    blocking_rm_count: int
    blocking_pm_count: int
    blocking_rm_materials: list[BlockingMaterialDetail] = Field(default_factory=list)
    blocking_pm_materials: list[BlockingMaterialDetail] = Field(default_factory=list)
    impacted_fg_materials: list[ImpactedFGDetail] = Field(default_factory=list)
    readiness_explanation: str
    evaluated_at: datetime


def evaluate_fg_production_readiness(
    db: Session,
    plant_code: str,
    fg_material_code: str,
    user_id: int | None = None,
) -> ProductionReadinessResult:
    """Production Readiness Engine combining Inventory Intelligence, RMPM Statistical Planning,

    RM Totality, PM Planning, and Dependency Intelligence to evaluate Finished Good production feasibility.
    """
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise ValueError(f"Plant '{plant_code}' not found.")

    fg_mat = db.query(Material).filter(Material.code == fg_material_code).first()
    if not fg_mat:
        raise ValueError(f"Finished Good '{fg_material_code}' not found.")

    # 1. Fetch FG Dependency Matrix (RM Totality + PM BOM/Override)
    matrix = get_fg_dependency_matrix(db, plant.id, fg_mat.id)

    blocking_rms: list[BlockingMaterialDetail] = []
    blocking_pms: list[BlockingMaterialDetail] = []

    # 2. Evaluate dependent Raw Materials
    for rm_dep in matrix.raw_materials:
        try:
            rm_plan = evaluate_material_planning(db, plant_code, rm_dep.rm_code)
            if rm_plan.rmpm_material_status in ("CRITICAL", "REORDER_REQUIRED") or rm_plan.planning_availability < rm_plan.trigger_2:
                blocking_rms.append(
                    BlockingMaterialDetail(
                        material_code=rm_dep.rm_code,
                        material_description=rm_dep.rm_description,
                        material_type="RM",
                        planning_available_stock=rm_plan.planning_availability,
                        trigger_2=rm_plan.trigger_2,
                        rmpm_status=rm_plan.rmpm_material_status,
                        reason=f"Raw Material '{rm_dep.rm_code}' breached stock threshold ({rm_plan.planning_availability:.1f} < {rm_plan.trigger_2:.1f}).",
                    )
                )
        except Exception:
            continue

    # 3. Evaluate dependent Packaging Materials
    for pm_dep in matrix.packaging_materials:
        try:
            pm_plan = evaluate_material_planning(db, plant_code, pm_dep.pm_code)
            if pm_plan.rmpm_material_status in ("CRITICAL", "REORDER_REQUIRED") or pm_plan.planning_availability < pm_plan.trigger_2:
                blocking_pms.append(
                    BlockingMaterialDetail(
                        material_code=pm_dep.pm_code,
                        material_description=pm_dep.pm_description,
                        material_type="PM",
                        planning_available_stock=pm_plan.planning_availability,
                        trigger_2=pm_plan.trigger_2,
                        rmpm_status=pm_plan.rmpm_material_status,
                        reason=f"Packaging Material '{pm_dep.pm_code}' breached stock threshold ({pm_plan.planning_availability:.1f} < {pm_plan.trigger_2:.1f}).",
                    )
                )
        except Exception:
            continue

    # 4. Determine final 4-tier Production Readiness status
    status: ProductionReadinessStatusEnum
    if blocking_rms and blocking_pms:
        status = "PRODUCTION_BLOCKED"
    elif blocking_rms and not blocking_pms:
        status = "RM_SHORTAGE"
    elif blocking_pms and not blocking_rms:
        status = "PM_SHORTAGE"
    else:
        status = "READY_TO_PRODUCE"

    # 5. Form Impacted Finished Goods list
    impacted_fgs: list[ImpactedFGDetail] = [
        ImpactedFGDetail(
            fg_code=fg_mat.code,
            fg_description=fg_mat.description,
            affected_by_rm=len(blocking_rms) > 0,
            affected_by_pm=len(blocking_pms) > 0,
        )
    ]

    # 6. Build Explainability Rationale
    if status == "READY_TO_PRODUCE":
        explanation = (
            f"READY TO PRODUCE: Finished Good '{fg_mat.code}' has 0 component shortages across all "
            f"{len(matrix.raw_materials)} Raw Materials and {len(matrix.packaging_materials)} Packaging Materials."
        )
    elif status == "RM_SHORTAGE":
        rm_names = ", ".join(b.material_code for b in blocking_rms)
        explanation = (
            f"RM SHORTAGE: Production of Finished Good '{fg_mat.code}' is constrained by {len(blocking_rms)} "
            f"Raw Material shortage(s) ({rm_names}). All Packaging Materials are healthy."
        )
    elif status == "PM_SHORTAGE":
        pm_names = ", ".join(b.material_code for b in blocking_pms)
        explanation = (
            f"PM SHORTAGE: Production of Finished Good '{fg_mat.code}' is constrained by {len(blocking_pms)} "
            f"Packaging Material shortage(s) ({pm_names}). All Raw Materials are healthy."
        )
    else:
        rm_names = ", ".join(b.material_code for b in blocking_rms)
        pm_names = ", ".join(b.material_code for b in blocking_pms)
        explanation = (
            f"PRODUCTION BLOCKED: Production of Finished Good '{fg_mat.code}' is blocked by dual shortages: "
            f"Raw Material(s) ({rm_names}) and Packaging Material(s) ({pm_names})."
        )

    now = datetime.now()

    # 7. Persist evaluation record in database
    details = {
        "status": status,
        "blocking_rms": [b.model_dump() for b in blocking_rms],
        "blocking_pms": [b.model_dump() for b in blocking_pms],
        "explanation": explanation,
    }
    rec = ProductionReadinessRecord(
        plant_id=plant.id,
        fg_material_id=fg_mat.id,
        status=status,
        blocking_rm_count=len(blocking_rms),
        blocking_pm_count=len(blocking_pms),
        details_json=json.dumps(details),
    )
    db.add(rec)
    db.flush()

    # 8. Record audit trail event
    record_audit_event(
        db,
        user_id=user_id,
        action="EVALUATE_PRODUCTION_READINESS",
        resource_type="ProductionReadinessRecord",
        resource_id=str(rec.id),
        details={
            "plant_code": plant_code,
            "fg_material_code": fg_material_code,
            "status": status,
            "blocking_rm_count": len(blocking_rms),
            "blocking_pm_count": len(blocking_pms),
        },
    )

    return ProductionReadinessResult(
        plant_code=plant_code,
        fg_code=fg_mat.code,
        fg_description=fg_mat.description,
        status=status,
        blocking_rm_count=len(blocking_rms),
        blocking_pm_count=len(blocking_pms),
        blocking_rm_materials=blocking_rms,
        blocking_pm_materials=blocking_pms,
        impacted_fg_materials=impacted_fgs,
        readiness_explanation=explanation,
        evaluated_at=now,
    )
