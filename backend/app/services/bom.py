from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import BOM, Material
from app.schemas.bom import BOMCreate, BOMUpdate


class BOMService:
    @staticmethod
    def get_boms(
        db: Session,
        fg_material_id: int | None = None,
        component_material_id: int | None = None,
        is_active: bool | None = None,
    ) -> Sequence[BOM]:
        query = db.query(BOM)
        if fg_material_id is not None:
            query = query.filter(BOM.fg_material_id == fg_material_id)
        if component_material_id is not None:
            query = query.filter(BOM.component_material_id == component_material_id)
        if is_active is not None:
            query = query.filter(BOM.is_active == is_active)
        return query.all()

    @staticmethod
    def get_bom_by_id(db: Session, bom_id: int) -> BOM:
        bom = db.query(BOM).filter(BOM.id == bom_id).first()
        if not bom:
            raise AppError("NOT_FOUND", f"BOM record with ID {bom_id} not found.", 404)
        return bom

    @staticmethod
    def create_bom(db: Session, bom_in: BOMCreate) -> BOM:
        if bom_in.fg_material_id == bom_in.component_material_id:
            raise AppError(
                "VALIDATION_ERROR",
                "FG material and component material cannot be identical.",
                400,
            )

        fg_mat = db.query(Material).filter(Material.id == bom_in.fg_material_id).first()
        if not fg_mat:
            raise AppError("NOT_FOUND", f"FG material with ID {bom_in.fg_material_id} not found.", 404)

        comp_mat = db.query(Material).filter(Material.id == bom_in.component_material_id).first()
        if not comp_mat:
            raise AppError(
                "NOT_FOUND",
                f"Component material with ID {bom_in.component_material_id} not found.",
                404,
            )

        existing = (
            db.query(BOM)
            .filter(
                BOM.fg_material_id == bom_in.fg_material_id,
                BOM.component_material_id == bom_in.component_material_id,
            )
            .first()
        )
        if existing:
            raise AppError(
                "CONFLICT",
                "A BOM mapping already exists for this FG and component material.",
                409,
            )

        bom = BOM(
            fg_material_id=bom_in.fg_material_id,
            component_material_id=bom_in.component_material_id,
            required_quantity=bom_in.required_quantity,
            unit_of_measure=bom_in.unit_of_measure,
            effective_from=bom_in.effective_from,
            effective_to=bom_in.effective_to,
            is_active=bom_in.is_active,
        )
        db.add(bom)
        db.commit()
        db.refresh(bom)
        return bom

    @staticmethod
    def update_bom(db: Session, bom_id: int, bom_in: BOMUpdate) -> BOM:
        bom = BOMService.get_bom_by_id(db, bom_id)
        update_data = bom_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(bom, field, value)

        db.add(bom)
        db.commit()
        db.refresh(bom)
        return bom

    @staticmethod
    def delete_bom(db: Session, bom_id: int) -> None:
        bom = BOMService.get_bom_by_id(db, bom_id)
        db.delete(bom)
        db.commit()
