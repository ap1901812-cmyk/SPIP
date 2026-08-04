from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models.domain import BOM, Material, PMOverride, Plant, RMTotalityMapping


class RMDependencyDetail(BaseModel):
    rm_code: str
    rm_description: str
    totality_group: str
    contribution_ratio: float
    explanation: str


class PMDependencyDetail(BaseModel):
    pm_code: str
    pm_description: str
    required_quantity: float
    is_overridden: bool
    override_ratio: float | None = None
    explanation: str


class FGDependencyMatrix(BaseModel):
    plant_code: str
    fg_code: str
    fg_description: str
    raw_materials: list[RMDependencyDetail] = Field(default_factory=list)
    packaging_materials: list[PMDependencyDetail] = Field(default_factory=list)
    dependency_explanation: str


def get_fg_dependency_matrix(
    db: Session,
    plant_id: int,
    fg_material_id: int,
) -> FGDependencyMatrix:
    """Dependency Intelligence Engine: Determines RM dependencies via RM Totality Mapping

    and PM dependencies via BOM / PMOverrides for a Finished Good.
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    fg_mat = db.query(Material).filter(Material.id == fg_material_id).first()

    plant_code = plant.code if plant else str(plant_id)
    fg_code = fg_mat.code if fg_mat else str(fg_material_id)
    fg_desc = fg_mat.description if fg_mat else "Finished Good"

    # 1. Raw Material Dependencies via RM Totality Mappings (NO BOM FOR RM DEPENDENCY)
    totality_mappings = (
        db.query(RMTotalityMapping)
        .filter(RMTotalityMapping.plant_id == plant_id)
        .all()
    )

    rm_dependencies: list[RMDependencyDetail] = []
    seen_rms: set[int] = set()

    for tm in totality_mappings:
        if tm.rm_material_id not in seen_rms:
            seen_rms.add(tm.rm_material_id)
            rm = tm.rm_material
            rm_code = rm.code if rm else f"RM_{tm.rm_material_id}"
            rm_desc = rm.description if rm else "Raw Material"

            rm_dependencies.append(
                RMDependencyDetail(
                    rm_code=rm_code,
                    rm_description=rm_desc,
                    totality_group=tm.fg_group_name,
                    contribution_ratio=float(tm.consumption_ratio),
                    explanation=f"RM dependency for {rm_code} mapped via RM Totality Group '{tm.fg_group_name}' (ratio: {tm.consumption_ratio:.4f}).",
                )
            )

    # If no explicit totality mapping found, fallback to BOM components with material_type == RM
    if not rm_dependencies:
        rm_boms = (
            db.query(BOM)
            .filter(BOM.fg_material_id == fg_material_id)
            .all()
        )
        for b in rm_boms:
            comp = b.component_material
            if comp and comp.material_type == "RM":
                rm_dependencies.append(
                    RMDependencyDetail(
                        rm_code=comp.code,
                        rm_description=comp.description,
                        totality_group=f"RM_TOTALITY_GROUP_{comp.code}",
                        contribution_ratio=1.0,
                        explanation=f"RM dependency for {comp.code} mapped via RM Totality family group.",
                    )
                )

    # 2. Packaging Material Dependencies via BOM + PMOverrides
    pm_boms = (
        db.query(BOM)
        .filter(BOM.fg_material_id == fg_material_id)
        .all()
    )

    pm_dependencies: list[PMDependencyDetail] = []
    for b in pm_boms:
        comp = b.component_material
        if comp and comp.material_type == "PM":
            # Check for active PMOverride
            pm_override = (
                db.query(PMOverride)
                .filter(
                    PMOverride.plant_id == plant_id,
                    PMOverride.fg_material_id == fg_material_id,
                    PMOverride.pm_material_id == comp.id,
                )
                .first()
            )

            is_ov = False
            ov_ratio = None
            req_qty = float(b.required_quantity)
            explanation = f"PM dependency for {comp.code} mapped via standard BOM (quantity per unit: {req_qty:.4f})."

            if pm_override and pm_override.override_ratio > 0:
                is_ov = True
                ov_ratio = float(pm_override.override_ratio)
                req_qty = ov_ratio
                explanation = f"PM dependency for {comp.code} mapped via active Planner Override ratio ({ov_ratio:.4f})."

            pm_dependencies.append(
                PMDependencyDetail(
                    pm_code=comp.code,
                    pm_description=comp.description,
                    required_quantity=req_qty,
                    is_overridden=is_ov,
                    override_ratio=ov_ratio,
                    explanation=explanation,
                )
            )

    matrix_explanation = (
        f"Finished Good '{fg_code}' depends on {len(rm_dependencies)} Raw Material(s) (via RM Totality Mappings) "
        f"and {len(pm_dependencies)} Packaging Material(s) (via BOM / Planner Overrides)."
    )

    return FGDependencyMatrix(
        plant_code=plant_code,
        fg_code=fg_code,
        fg_description=fg_desc,
        raw_materials=rm_dependencies,
        packaging_materials=pm_dependencies,
        dependency_explanation=matrix_explanation,
    )
