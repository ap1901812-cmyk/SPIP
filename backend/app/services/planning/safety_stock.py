from __future__ import annotations

import math
from typing import NamedTuple

from app.db.models.domain import PlantMaterial


class SafetyStockResult(NamedTuple):
    safety_stock: float
    is_overridden: bool
    service_level_z: float
    abc_class: str


def calculate_safety_stock(
    demand_std_dev: float,
    lead_time_days: float,
    plant_material: PlantMaterial | None = None,
) -> SafetyStockResult:
    """Calculates V1 Safety Stock using SS = Z * sigma_d * sqrt(LT).
    Applies configurable ABC class Z factors, min floors, max ceilings, and manual overrides.
    """
    z_factor = plant_material.service_level_z if plant_material else 1.65
    abc_class = plant_material.abc_class if plant_material else "B"

    # Manual override check
    if plant_material and plant_material.safety_stock_override is not None:
        return SafetyStockResult(
            safety_stock=round(float(plant_material.safety_stock_override), 4),
            is_overridden=True,
            service_level_z=z_factor,
            abc_class=abc_class,
        )

    if demand_std_dev <= 0 or lead_time_days <= 0:
        raw_ss = 0.0
    else:
        raw_ss = z_factor * demand_std_dev * math.sqrt(lead_time_days)

    # Apply min floor
    min_floor = plant_material.min_safety_stock if plant_material else 0.0
    if min_floor is not None and raw_ss < min_floor:
        raw_ss = min_floor

    # Apply max ceiling
    max_ceiling = plant_material.max_safety_stock if plant_material else None
    if max_ceiling is not None and raw_ss > max_ceiling:
        raw_ss = max_ceiling

    return SafetyStockResult(
        safety_stock=round(raw_ss, 4),
        is_overridden=False,
        service_level_z=z_factor,
        abc_class=abc_class,
    )
