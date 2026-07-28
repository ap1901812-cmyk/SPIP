from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.db.models.domain import BOM, Material, MaterialTypeEnum
from app.schemas.dependency import (
    MaterialDependencyResponse,
    WhereUsedEntry,
    WhereUsedResponse,
)


class DependencyService:
    @staticmethod
    def _to_where_used_entry(bom: BOM, use_component_as_target: bool = False) -> WhereUsedEntry:
        target_mat = bom.component_material if use_component_as_target else bom.fg_material
        target_id = bom.component_material_id if use_component_as_target else bom.fg_material_id

        return WhereUsedEntry(
            bom_id=bom.id,
            fg_material_id=target_id,
            fg_code=target_mat.code if target_mat else "",
            fg_description=target_mat.description if target_mat else "",
            fg_material_type=MaterialTypeEnum.normalize(target_mat.material_type) if target_mat else "FG",
            required_quantity=bom.required_quantity,
            unit_of_measure=bom.unit_of_measure,
            is_active=bom.is_active,
        )

    @staticmethod
    def get_where_used(db: Session, material_id: int) -> WhereUsedResponse:
        mat = db.query(Material).filter(Material.id == material_id).first()
        if not mat:
            raise AppError("NOT_FOUND", f"Material with ID {material_id} not found.", 404)

        boms = (
            db.query(BOM)
            .options(joinedload(BOM.fg_material))
            .filter(BOM.component_material_id == material_id)
            .all()
        )
        where_used_entries = [DependencyService._to_where_used_entry(b, use_component_as_target=False) for b in boms]

        return WhereUsedResponse(
            component_material_id=mat.id,
            component_code=mat.code,
            component_description=mat.description,
            component_type=MaterialTypeEnum.normalize(mat.material_type),
            total_where_used=len(where_used_entries),
            where_used=where_used_entries,
        )

    @staticmethod
    def get_material_dependencies(db: Session, material_id: int) -> MaterialDependencyResponse:
        mat = db.query(Material).filter(Material.id == material_id).first()
        if not mat:
            raise AppError("NOT_FOUND", f"Material with ID {material_id} not found.", 404)

        # Upstream FGs (where this material is a component)
        upstream_boms = (
            db.query(BOM)
            .options(joinedload(BOM.fg_material))
            .filter(BOM.component_material_id == material_id)
            .all()
        )
        upstream_entries = [
            DependencyService._to_where_used_entry(b, use_component_as_target=False)
            for b in upstream_boms
        ]

        # Downstream components (where this material is an FG)
        downstream_boms = (
            db.query(BOM)
            .options(joinedload(BOM.component_material))
            .filter(BOM.fg_material_id == material_id)
            .all()
        )
        downstream_entries = [
            DependencyService._to_where_used_entry(b, use_component_as_target=True)
            for b in downstream_boms
        ]

        return MaterialDependencyResponse(
            material_id=mat.id,
            material_code=mat.code,
            material_description=mat.description,
            material_type=MaterialTypeEnum.normalize(mat.material_type),
            upstream_finished_goods=upstream_entries,
            downstream_components=downstream_entries,
        )
