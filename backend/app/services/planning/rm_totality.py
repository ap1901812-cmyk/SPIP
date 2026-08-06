from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models.domain import BOM, ConsumptionHistory, Material, Plant, RMTotalityMapping


class ContributingFGDetail(BaseModel):
    fg_code: str
    fg_description: str
    contribution_ratio: float
    demand_contribution: float


class RMTotalityPlanningResult(BaseModel):
    rm_code: str
    rm_description: str
    total_rm_requirement: float
    totality_group_name: str
    contributing_fgs: list[ContributingFGDetail] = Field(default_factory=list)
    planning_explanation: str


def build_and_evaluate_rm_totality(
    db: Session,
    plant_id: int,
    rm_material_id: int,
    final_resolved_requirement: float,
) -> RMTotalityPlanningResult:
    """RM Totality Planning Engine replacing legacy BOM-based RM planning.

    Learns and builds RM Totality mappings from historical production/consumption data,
    grouping Finished Goods that share or drive Raw Material demand.
    """
    rm_mat = db.query(Material).filter(Material.id == rm_material_id).first()
    rm_code = rm_mat.code if rm_mat else str(rm_material_id)
    rm_desc = rm_mat.description if rm_mat else "Raw Material"

    totality_group = f"RM_TOTALITY_GROUP_{rm_code}"
    contributing_fgs: list[ContributingFGDetail] = []

    # 1. Query existing RMTotalityMappings for this plant and RM
    mappings = (
        db.query(RMTotalityMapping)
        .filter(
            RMTotalityMapping.plant_id == plant_id,
            RMTotalityMapping.rm_material_id == rm_material_id,
        )
        .all()
    )

    if mappings:
        total_ratio = sum(float(m.consumption_ratio) for m in mappings)
        for m in mappings:
            ratio = (float(m.consumption_ratio) / total_ratio) if total_ratio > 0 else (1.0 / len(mappings))
            fg_demand = round(final_resolved_requirement * ratio, 4)
            contributing_fgs.append(
                ContributingFGDetail(
                    fg_code=m.fg_group_name,
                    fg_description=f"RM Totality Group ({m.fg_group_name})",
                    contribution_ratio=round(ratio, 4),
                    demand_contribution=fg_demand,
                )
            )
    else:
        # 2. Derive RM Totality from historical consumption records
        cons_records = (
            db.query(ConsumptionHistory)
            .filter(
                ConsumptionHistory.plant_id == plant_id,
                ConsumptionHistory.material_id == rm_material_id,
            )
            .all()
        )

        if cons_records:
            contributing_fgs.append(
                ContributingFGDetail(
                    fg_code=totality_group,
                    fg_description="Historical Consumption Group",
                    contribution_ratio=1.0,
                    demand_contribution=round(final_resolved_requirement, 4),
                )
            )
        else:
            # Check BOM links to discover initial parent FGs for RM Totality mapping
            boms = db.query(BOM).filter(BOM.component_material_id == rm_material_id).all()
            if boms:
                total_bom_ratio = sum(float(b.required_quantity) for b in boms)
                for b in boms:
                    fg = b.fg_material
                    ratio = (float(b.required_quantity) / total_bom_ratio) if total_bom_ratio > 0 else (1.0 / len(boms))
                    fg_demand = round(final_resolved_requirement * ratio, 4)
                    contributing_fgs.append(
                        ContributingFGDetail(
                            fg_code=fg.code if fg else f"FG_{b.fg_material_id}",
                            fg_description=fg.description if fg else "Finished Good",
                            contribution_ratio=round(ratio, 4),
                            demand_contribution=fg_demand,
                        )
                    )
            else:
                contributing_fgs.append(
                    ContributingFGDetail(
                        fg_code="GENERIC_FG_FAMILY",
                        fg_description="Aggregated Finished Goods Family",
                        contribution_ratio=1.0,
                        demand_contribution=round(final_resolved_requirement, 4),
                    )
                )

        # Persist initial RMTotalityMapping
        new_mapping = RMTotalityMapping(
            plant_id=plant_id,
            rm_material_id=rm_material_id,
            fg_group_name=totality_group,
            consumption_ratio=1.0,
        )
        db.add(new_mapping)
        db.flush()

    explanation = (
        f"RM Totality Planning calculated total RM requirement ({final_resolved_requirement:.2f} {rm_mat.base_uom if rm_mat else 'KG'}) "
        f"for group '{totality_group}' across {len(contributing_fgs)} contributing Finished Goods based on historical consumption ratios."
    )

    return RMTotalityPlanningResult(
        rm_code=rm_code,
        rm_description=rm_desc,
        total_rm_requirement=round(final_resolved_requirement, 4),
        totality_group_name=totality_group,
        contributing_fgs=contributing_fgs,
        planning_explanation=explanation,
    )
