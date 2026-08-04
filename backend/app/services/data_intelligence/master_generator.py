from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.audit import record_audit_event
from app.db.models.domain import Material, MaterialTypeEnum, Plant, Vendor


class AutoMasterGenerator:
    """Service to derive and automatically generate missing master records with audit logging."""

    def __init__(self, db: Session, user_id: int | None = None) -> None:
        self.db = db
        self.user_id = user_id
        self._plant_cache: dict[str, Plant] = {p.code: p for p in db.query(Plant).all()}
        self._material_cache: dict[str, Material] = {m.code: m for m in db.query(Material).all()}
        self._vendor_cache: dict[str, Vendor] = {v.code: v for v in db.query(Vendor).all()}

    def get_or_create_plant(
        self,
        plant_code: str,
        plant_name: str | None = None,
        location: str | None = None,
    ) -> tuple[Plant, bool]:
        p_code = plant_code.strip()
        if not p_code:
            raise ValueError("Plant code cannot be empty.")

        if p_code in self._plant_cache:
            return self._plant_cache[p_code], False

        name = plant_name.strip() if plant_name else f"Auto Generated Plant {p_code}"
        plant = Plant(code=p_code, name=name, location=location)
        self.db.add(plant)
        self.db.flush()

        self._plant_cache[p_code] = plant

        # Create audit trail
        record_audit_event(
            self.db,
            user_id=self.user_id,
            action="AUTO_GENERATE_PLANT_MASTER",
            resource_type="Plant",
            resource_id=str(plant.id),
            details={"code": p_code, "name": name, "auto_generated": True},
        )
        return plant, True

    def get_or_create_material(
        self,
        material_code: str,
        description: str | None = None,
        material_type: str | None = None,
        base_uom: str = "KG",
    ) -> tuple[Material, bool]:
        m_code = material_code.strip()
        if not m_code:
            raise ValueError("Material code cannot be empty.")

        if m_code in self._material_cache:
            return self._material_cache[m_code], False

        desc = description.strip() if description else f"Auto Generated Material {m_code}"
        m_type = MaterialTypeEnum.normalize(material_type) if material_type else MaterialTypeEnum.RM.value

        material = Material(
            code=m_code,
            description=desc,
            material_type=m_type,
            base_uom=base_uom or "KG",
        )
        self.db.add(material)
        self.db.flush()

        self._material_cache[m_code] = material

        # Create audit trail
        record_audit_event(
            self.db,
            user_id=self.user_id,
            action="AUTO_GENERATE_MATERIAL_MASTER",
            resource_type="Material",
            resource_id=str(material.id),
            details={
                "code": m_code,
                "description": desc,
                "material_type": m_type,
                "base_uom": base_uom,
                "auto_generated": True,
            },
        )
        return material, True

    def get_or_create_vendor(
        self,
        vendor_code: str,
        vendor_name: str | None = None,
        contact_email: str | None = None,
    ) -> tuple[Vendor, bool]:
        v_code = vendor_code.strip()
        if not v_code:
            raise ValueError("Vendor code cannot be empty.")

        if v_code in self._vendor_cache:
            return self._vendor_cache[v_code], False

        name = vendor_name.strip() if vendor_name else f"Auto Generated Vendor {v_code}"
        vendor = Vendor(code=v_code, name=name, contact_email=contact_email)
        self.db.add(vendor)
        self.db.flush()

        self._vendor_cache[v_code] = vendor

        # Create audit trail
        record_audit_event(
            self.db,
            user_id=self.user_id,
            action="AUTO_GENERATE_VENDOR_MASTER",
            resource_type="Vendor",
            resource_id=str(vendor.id),
            details={"code": v_code, "name": name, "auto_generated": True},
        )
        return vendor, True
