from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.db.models.domain import PlantMaterial, VendorMaterial


class DualLeadTimeResult(NamedTuple):
    lead_time_1: float
    lead_time_2: float
    source_lt1: str
    source_lt2: str


def resolve_dual_lead_time(
    db: Session,
    plant_id: int,
    material_id: int,
    plant_material: PlantMaterial | None = None,
) -> DualLeadTimeResult:
    """Resolves RMPM Dual Lead Times (LT-1 and LT-2) without undocumented heuristics.

    Uses authoritative parameter sources:
    1. PlantMaterial explicit lead_time_1 and lead_time_2
    2. Primary Vendor lead_time_1_days and lead_time_2_days
    3. PlantMaterial legacy lead_time_days
    4. Approved system fallback (7.0 days for LT-1, 3.0 days for LT-2)
    """
    pm = plant_material or (
        db.query(PlantMaterial)
        .filter(PlantMaterial.plant_id == plant_id, PlantMaterial.material_id == material_id)
        .first()
    )

    # 1. Check PlantMaterial explicit RMPM lead times
    lt1 = float(pm.lead_time_1) if (pm and pm.lead_time_1 and pm.lead_time_1 > 0) else None
    lt2 = float(pm.lead_time_2) if (pm and pm.lead_time_2 and pm.lead_time_2 > 0) else None
    source_lt1 = "PLANT_MATERIAL_LT1" if lt1 else ""
    source_lt2 = "PLANT_MATERIAL_LT2" if lt2 else ""

    # 2. Check Primary Vendor lead times if missing
    if not lt1 or not lt2:
        primary_vm = (
            db.query(VendorMaterial)
            .filter(
                VendorMaterial.plant_id == plant_id,
                VendorMaterial.material_id == material_id,
                VendorMaterial.is_primary == True,  # noqa: E712
            )
            .first()
        )
        if primary_vm and primary_vm.vendor:
            vendor = primary_vm.vendor
            if not lt1 and vendor.lead_time_1_days and vendor.lead_time_1_days > 0:
                lt1 = float(vendor.lead_time_1_days)
                source_lt1 = f"PRIMARY_VENDOR_{vendor.code}_LT1"
            if not lt2 and vendor.lead_time_2_days and vendor.lead_time_2_days > 0:
                lt2 = float(vendor.lead_time_2_days)
                source_lt2 = f"PRIMARY_VENDOR_{vendor.code}_LT2"

            if not lt1 and primary_vm.vendor_lead_time_days and primary_vm.vendor_lead_time_days > 0:
                lt1 = float(primary_vm.vendor_lead_time_days)
                source_lt1 = f"PRIMARY_VENDOR_{vendor.code}_LEGACY"

    # 3. Check PlantMaterial legacy lead_time_days if still missing
    if not lt1 and pm and pm.lead_time_days and pm.lead_time_days > 0:
        lt1 = float(pm.lead_time_days)
        source_lt1 = "PLANT_MATERIAL_LEGACY"

    # 4. Fallback hierarchy (7.0 for LT-1, 3.0 for LT-2)
    if not lt1:
        lt1 = 7.0
        source_lt1 = "DEFAULT_FALLBACK"

    if not lt2:
        lt2 = 3.0 if lt1 >= 3.0 else lt1
        source_lt2 = "DEFAULT_FALLBACK"

    return DualLeadTimeResult(
        lead_time_1=round(lt1, 2),
        lead_time_2=round(lt2, 2),
        source_lt1=source_lt1,
        source_lt2=source_lt2,
    )


class LeadTimeResult(NamedTuple):
    lead_time_days: float
    source: str


def resolve_lead_time(
    db: Session,
    plant_id: int,
    material_id: int,
    plant_material: PlantMaterial | None = None,
) -> LeadTimeResult:
    """Legacy backward-compatible wrapper returning single lead time (LT-1)."""
    res = resolve_dual_lead_time(db, plant_id, material_id, plant_material=plant_material)
    return LeadTimeResult(lead_time_days=res.lead_time_1, source=res.source_lt1)
