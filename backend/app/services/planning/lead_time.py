from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.db.models.domain import PlantMaterial, VendorMaterial


class LeadTimeResult(NamedTuple):
    lead_time_days: float
    source: str


def resolve_lead_time(
    db: Session,
    plant_id: int,
    material_id: int,
    plant_material: PlantMaterial | None = None,
) -> LeadTimeResult:
    """Resolves lead time using authoritative ordered fallback logic:
    1. Primary vendor lead time for plant-material
    2. Configured plant-material lead time
    3. Default fallback (7.0 days)
    """
    # 1. Check primary vendor lead time
    primary_vm = (
        db.query(VendorMaterial)
        .filter(
            VendorMaterial.plant_id == plant_id,
            VendorMaterial.material_id == material_id,
            VendorMaterial.is_primary == True,  # noqa: E712
        )
        .first()
    )
    if primary_vm and primary_vm.vendor_lead_time_days and primary_vm.vendor_lead_time_days > 0:
        return LeadTimeResult(
            lead_time_days=float(primary_vm.vendor_lead_time_days),
            source=f"PRIMARY_VENDOR_{primary_vm.vendor.code if primary_vm.vendor else 'MASTER'}",
        )

    # 2. Check plant-material configured lead time
    pm = plant_material or (
        db.query(PlantMaterial)
        .filter(PlantMaterial.plant_id == plant_id, PlantMaterial.material_id == material_id)
        .first()
    )
    if pm and pm.lead_time_days and pm.lead_time_days > 0:
        return LeadTimeResult(
            lead_time_days=float(pm.lead_time_days),
            source="PLANT_MATERIAL_MASTER",
        )

    # 3. Default fallback
    return LeadTimeResult(lead_time_days=7.0, source="DEFAULT_FALLBACK")
