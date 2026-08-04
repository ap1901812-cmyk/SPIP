from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.db.models.domain import Material, PMOverride, Plant
from app.db.models.user import RoleEnum, User
from app.services.planning.pm_planning import create_or_update_pm_override

router = APIRouter(prefix="/planning/pm-overrides", tags=["pm-overrides"])

planner_or_admin_role = require_roles(RoleEnum.PLANNER, RoleEnum.ADMIN)


class PMOverrideRequest(BaseModel):
    plant_code: str
    fg_material_code: str
    pm_material_code: str
    override_ratio: float = Field(..., gt=0.0, description="Override multiplier ratio for PM planning")
    notes: str | None = None


@router.post(
    "",
    dependencies=[Depends(planner_or_admin_role)],
)
def submit_pm_override(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    request: PMOverrideRequest,
) -> dict[str, Any]:
    """Create or update a Packaging Material (PM) planning override ratio."""
    plant = db.query(Plant).filter(Plant.code == request.plant_code).first()
    if not plant:
        return {"status": "ERROR", "message": f"Plant '{request.plant_code}' not found."}

    fg_mat = db.query(Material).filter(Material.code == request.fg_material_code).first()
    if not fg_mat:
        return {"status": "ERROR", "message": f"FG Material '{request.fg_material_code}' not found."}

    pm_mat = db.query(Material).filter(Material.code == request.pm_material_code).first()
    if not pm_mat:
        return {"status": "ERROR", "message": f"PM Material '{request.pm_material_code}' not found."}

    override = create_or_update_pm_override(
        db=db,
        plant_id=plant.id,
        fg_material_id=fg_mat.id,
        pm_material_id=pm_mat.id,
        override_ratio=request.override_ratio,
        notes=request.notes,
        user_id=current_user.id,
    )

    return {
        "id": override.id,
        "plant_code": plant.code,
        "fg_material_code": fg_mat.code,
        "pm_material_code": pm_mat.code,
        "override_ratio": override.override_ratio,
        "notes": override.notes,
        "updated_by": current_user.email,
        "updated_at": override.updated_at.isoformat(),
    }


@router.get(
    "",
    dependencies=[Depends(planner_or_admin_role)],
)
def list_pm_overrides(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(planner_or_admin_role)],
    plant_code: str = Query(..., description="Target plant code"),
) -> list[dict[str, Any]]:
    """List active PM planner overrides for a plant."""
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        return []

    overrides = (
        db.query(PMOverride)
        .filter(PMOverride.plant_id == plant.id)
        .order_by(PMOverride.updated_at.desc())
        .all()
    )

    return [
        {
            "id": ov.id,
            "plant_code": plant_code,
            "fg_material_code": ov.fg_material.code if ov.fg_material else str(ov.fg_material_id),
            "pm_material_code": ov.pm_material.code if ov.pm_material else str(ov.pm_material_id),
            "override_ratio": ov.override_ratio,
            "notes": ov.notes,
            "updated_by": ov.updated_by_user.email if ov.updated_by_user else None,
            "updated_at": ov.updated_at.isoformat(),
        }
        for ov in overrides
    ]
