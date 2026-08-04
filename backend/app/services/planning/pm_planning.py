from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.db.models.domain import BOM, Material, PMOverride, Plant


class PMPlanningResult(BaseModel):
    pm_code: str
    pm_description: str
    fg_code: str
    bom_quantity: float
    override_ratio: float | None = None
    override_quantity: float | None = None
    quantity_used_for_planning: float
    is_overridden: bool = False
    override_user_email: str | None = None
    override_timestamp: datetime | None = None
    planning_explanation: str


def evaluate_pm_planning(
    db: Session,
    plant_id: int,
    pm_material_id: int,
    fg_material_id: int,
    fg_requirement: float,
) -> PMPlanningResult:
    """PM Planning Engine using standard BOM as default with optional Planner Override support."""
    pm_mat = db.query(Material).filter(Material.id == pm_material_id).first()
    fg_mat = db.query(Material).filter(Material.id == fg_material_id).first()

    pm_code = pm_mat.code if pm_mat else str(pm_material_id)
    pm_desc = pm_mat.description if pm_mat else "Packaging Material"
    fg_code = fg_mat.code if fg_mat else str(fg_material_id)

    # 1. Fetch standard BOM ratio
    bom = (
        db.query(BOM)
        .filter(
            BOM.fg_material_id == fg_material_id,
            BOM.component_material_id == pm_material_id,
        )
        .first()
    )
    bom_ratio = float(bom.required_quantity) if bom else 1.0
    bom_qty = round(fg_requirement * bom_ratio, 4)

    # 2. Check for active PMOverride
    query_override = db.query(PMOverride).filter(
        PMOverride.plant_id == plant_id,
        PMOverride.pm_material_id == pm_material_id,
    )
    if fg_material_id != pm_material_id:
        query_override = query_override.filter(PMOverride.fg_material_id == fg_material_id)

    pm_override = query_override.first()

    if pm_override and pm_override.override_ratio > 0:
        ov_ratio = float(pm_override.override_ratio)
        ov_qty = round(fg_requirement * ov_ratio, 4)
        user_email = pm_override.updated_by_user.email if pm_override.updated_by_user else "Planner"
        updated_at = pm_override.updated_at

        explanation = (
            f"PM Requirement calculated using Planner Override ratio ({ov_ratio:.4f}) set by {user_email} "
            f"on {updated_at.isoformat()} instead of standard BOM ratio ({bom_ratio:.4f})."
        )
        return PMPlanningResult(
            pm_code=pm_code,
            pm_description=pm_desc,
            fg_code=fg_code,
            bom_quantity=bom_qty,
            override_ratio=ov_ratio,
            override_quantity=ov_qty,
            quantity_used_for_planning=ov_qty,
            is_overridden=True,
            override_user_email=user_email,
            override_timestamp=updated_at,
            planning_explanation=explanation,
        )

    # Default BOM calculation
    explanation = f"PM Requirement calculated using standard BOM ratio ({bom_ratio:.4f})."
    return PMPlanningResult(
        pm_code=pm_code,
        pm_description=pm_desc,
        fg_code=fg_code,
        bom_quantity=bom_qty,
        quantity_used_for_planning=bom_qty,
        is_overridden=False,
        planning_explanation=explanation,
    )


def create_or_update_pm_override(
    db: Session,
    plant_id: int,
    fg_material_id: int,
    pm_material_id: int,
    override_ratio: float,
    notes: str | None = None,
    user_id: int | None = None,
) -> PMOverride:
    """Submit or update a PM planner override ratio."""
    pm_override = (
        db.query(PMOverride)
        .filter(
            PMOverride.plant_id == plant_id,
            PMOverride.fg_material_id == fg_material_id,
            PMOverride.pm_material_id == pm_material_id,
        )
        .first()
    )

    if not pm_override:
        pm_override = PMOverride(
            plant_id=plant_id,
            fg_material_id=fg_material_id,
            pm_material_id=pm_material_id,
            override_ratio=override_ratio,
            notes=notes,
            updated_by_user_id=user_id,
        )
        db.add(pm_override)
    else:
        pm_override.override_ratio = override_ratio
        pm_override.notes = notes
        pm_override.updated_by_user_id = user_id

    db.commit()
    db.refresh(pm_override)

    # Log audit event
    record_audit_event(
        db,
        user_id=user_id,
        action="CREATE_OR_UPDATE_PM_OVERRIDE",
        resource_type="PMOverride",
        resource_id=str(pm_override.id),
        details={
            "plant_id": plant_id,
            "fg_material_id": fg_material_id,
            "pm_material_id": pm_material_id,
            "override_ratio": override_ratio,
            "notes": notes,
        },
    )
    return pm_override
