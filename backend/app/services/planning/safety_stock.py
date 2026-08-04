from __future__ import annotations

import math
from typing import NamedTuple

from app.db.models.domain import PlantMaterial


class SafetyStockResult(NamedTuple):
    safety_stock: float
    is_overridden: bool
    service_level_z: float
    abc_class: str


class DualSafetyStockResult(NamedTuple):
    safety_stock_1: float
    safety_stock_2: float
    is_overridden: bool
    service_level_z: float
    abc_class: str


def calculate_safety_stock(
    demand_std_dev: float,
    lead_time_days: float,
    plant_material: PlantMaterial | None = None,
) -> SafetyStockResult:
    """Calculates legacy V1 Safety Stock using SS = Z * sigma_d * sqrt(LT)."""
    z_factor = plant_material.service_level_z if plant_material else 1.65
    abc_class = plant_material.abc_class if plant_material else "B"

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

    min_floor = plant_material.min_safety_stock if plant_material else 0.0
    if min_floor is not None and raw_ss < min_floor:
        raw_ss = min_floor

    max_ceiling = plant_material.max_safety_stock if plant_material else None
    if max_ceiling is not None and raw_ss > max_ceiling:
        raw_ss = max_ceiling

    return SafetyStockResult(
        safety_stock=round(raw_ss, 4),
        is_overridden=False,
        service_level_z=z_factor,
        abc_class=abc_class,
    )


def calculate_dual_safety_stock(
    demand_std_dev: float,
    lead_time_1: float,
    lead_time_2: float,
    plant_material: PlantMaterial | None = None,
) -> DualSafetyStockResult:
    """Calculates RMPM Dual Safety Stocks (SS-1 and SS-2):

    SS-1 = Z * sigma_d * sqrt(LT-1)
    SS-2 = Z * sigma_d * sqrt(LT-2)
    Applies overrides, min floor, and max ceiling constraints.
    """
    z_factor = plant_material.service_level_z if plant_material else 1.65
    abc_class = plant_material.abc_class if plant_material else "B"

    if plant_material and plant_material.safety_stock_1 is not None and plant_material.safety_stock_2 is not None:
        return DualSafetyStockResult(
            safety_stock_1=round(float(plant_material.safety_stock_1), 4),
            safety_stock_2=round(float(plant_material.safety_stock_2), 4),
            is_overridden=False,
            service_level_z=z_factor,
            abc_class=abc_class,
        )

    if plant_material and plant_material.safety_stock_override is not None:
        ov = round(float(plant_material.safety_stock_override), 4)
        return DualSafetyStockResult(
            safety_stock_1=ov,
            safety_stock_2=ov,
            is_overridden=True,
            service_level_z=z_factor,
            abc_class=abc_class,
        )

    if demand_std_dev <= 0:
        ss1, ss2 = 0.0, 0.0
    else:
        ss1 = z_factor * demand_std_dev * math.sqrt(max(0.0, lead_time_1))
        ss2 = z_factor * demand_std_dev * math.sqrt(max(0.0, lead_time_2))

    min_floor = plant_material.min_safety_stock if plant_material else 0.0
    max_ceiling = plant_material.max_safety_stock if plant_material else None

    if min_floor is not None:
        ss1 = max(min_floor, ss1)
        ss2 = max(min_floor, ss2)

    if max_ceiling is not None:
        ss1 = min(max_ceiling, ss1)
        ss2 = min(max_ceiling, ss2)

    return DualSafetyStockResult(
        safety_stock_1=round(ss1, 4),
        safety_stock_2=round(ss2, 4),
        is_overridden=False,
        service_level_z=z_factor,
        abc_class=abc_class,
    )
