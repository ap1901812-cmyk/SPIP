from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import AppError
from app.db.models.domain import BOM, InventorySnapshot, Material, MaterialTypeEnum, PlantMaterial
from app.schemas.bom import BOMDetailResponse
from app.schemas.domain import InventorySnapshotResponse, PlantMaterialResponse
from app.schemas.finished_goods import (
    FGBOMExpansionResponse,
    FinishedGoodDetail,
    FinishedGoodSummary,
)


class FinishedGoodsService:
    @staticmethod
    def get_finished_goods(db: Session, plant_id: int | None = None) -> list[FinishedGoodSummary]:
        query = db.query(Material).filter(
            (Material.material_type == MaterialTypeEnum.FG.value)
            | (Material.material_type == "FINISHED_GOOD")
        )

        if plant_id is not None:
            query = query.join(PlantMaterial, PlantMaterial.material_id == Material.id).filter(
                PlantMaterial.plant_id == plant_id
            )

        fg_materials = query.all()
        if not fg_materials:
            return []

        fg_ids = [m.id for m in fg_materials]

        # Aggregate plant counts for all target FGs in a single SQL query
        plant_counts = (
            db.query(PlantMaterial.material_id, func.count(PlantMaterial.id))
            .filter(PlantMaterial.material_id.in_(fg_ids))
            .group_by(PlantMaterial.material_id)
            .all()
        )
        plant_count_map = {mat_id: count for mat_id, count in plant_counts}

        # Aggregate component counts for all target FGs in a single SQL query
        component_counts = (
            db.query(BOM.fg_material_id, func.count(BOM.id))
            .filter(BOM.fg_material_id.in_(fg_ids))
            .group_by(BOM.fg_material_id)
            .all()
        )
        component_count_map = {fg_id: count for fg_id, count in component_counts}

        summaries: list[FinishedGoodSummary] = []
        for mat in fg_materials:
            summaries.append(
                FinishedGoodSummary(
                    id=mat.id,
                    code=mat.code,
                    description=mat.description,
                    base_uom=mat.base_uom,
                    material_type=MaterialTypeEnum.normalize(mat.material_type),
                    plant_count=plant_count_map.get(mat.id, 0),
                    component_count=component_count_map.get(mat.id, 0),
                    created_at=mat.created_at,
                    updated_at=mat.updated_at,
                )
            )

        return summaries

    @staticmethod
    def get_finished_good_by_id(db: Session, fg_id: int) -> FinishedGoodDetail:
        mat = (
            db.query(Material)
            .options(
                selectinload(Material.plant_materials),
                selectinload(Material.boms_as_fg).joinedload(BOM.component_material),
            )
            .filter(Material.id == fg_id)
            .first()
        )

        if not mat:
            raise AppError("NOT_FOUND", f"Finished Good with ID {fg_id} not found.", 404)

        if not MaterialTypeEnum.is_fg(mat.material_type):
            raise AppError(
                "VALIDATION_ERROR",
                f"Material {mat.code} is of type '{mat.material_type}', not a Finished Good (FG).",
                400,
            )

        inventory_snapshots = (
            db.query(InventorySnapshot).filter(InventorySnapshot.material_id == mat.id).all()
        )

        boms = mat.boms_as_fg
        rm_count = sum(
            1
            for b in boms
            if b.component_material and MaterialTypeEnum.is_rm(b.component_material.material_type)
        )
        pm_count = sum(
            1
            for b in boms
            if b.component_material and MaterialTypeEnum.is_pm(b.component_material.material_type)
        )

        return FinishedGoodDetail(
            id=mat.id,
            code=mat.code,
            description=mat.description,
            base_uom=mat.base_uom,
            material_type=MaterialTypeEnum.normalize(mat.material_type),
            created_at=mat.created_at,
            updated_at=mat.updated_at,
            plant_materials=[PlantMaterialResponse.model_validate(pm) for pm in mat.plant_materials],
            inventory_snapshots=[
                InventorySnapshotResponse.model_validate(inv) for inv in inventory_snapshots
            ],
            rm_components_count=rm_count,
            pm_components_count=pm_count,
        )

    @staticmethod
    def get_fg_bom_expansion(db: Session, fg_id: int) -> FGBOMExpansionResponse:
        mat = db.query(Material).filter(Material.id == fg_id).first()
        if not mat:
            raise AppError("NOT_FOUND", f"Material with ID {fg_id} not found.", 404)

        boms = (
            db.query(BOM)
            .options(joinedload(BOM.component_material))
            .filter(BOM.fg_material_id == fg_id)
            .all()
        )

        rm_components: list[BOMDetailResponse] = []
        pm_components: list[BOMDetailResponse] = []

        for b in boms:
            detail = BOMDetailResponse.model_validate(b)
            comp_type = b.component_material.material_type if b.component_material else ""
            if MaterialTypeEnum.is_pm(comp_type):
                pm_components.append(detail)
            else:
                rm_components.append(detail)

        return FGBOMExpansionResponse(
            fg_material_id=mat.id,
            fg_code=mat.code,
            fg_description=mat.description,
            rm_components=rm_components,
            pm_components=pm_components,
        )
