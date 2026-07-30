from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models.domain import Material, Plant, PlantMaterial
from app.schemas.planning import PlanningCalculationResult
from app.services.planning.availability import calculate_planning_availability
from app.services.planning.lead_time import resolve_lead_time
from app.services.planning.safety_stock import calculate_safety_stock
from app.services.planning.statistics import calculate_demand_statistics


class PlanningEngineError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("PLANNING_ENGINE_ERROR", message, 404)


def evaluate_material_planning(
    db: Session,
    plant_code: str,
    material_code: str,
    as_of_datetime: datetime | None = None,
    statistics_window_days: int | None = None,
    decision_horizon_days: int | None = None,
) -> PlanningCalculationResult:
    """Evaluates material planning decision rules for a specific plant and material.
    Returns deterministic, explainable PlanningCalculationResult.
    """
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise PlanningEngineError(f"Plant with code '{plant_code}' not found.")

    material = db.query(Material).filter(Material.code == material_code).first()
    if not material:
        raise PlanningEngineError(f"Material with code '{material_code}' not found.")

    pm = (
        db.query(PlantMaterial)
        .filter(PlantMaterial.plant_id == plant.id, PlantMaterial.material_id == material.id)
        .first()
    )

    cfg = get_settings()
    stat_days = (
        statistics_window_days
        if statistics_window_days is not None
        else cfg.planning_statistics_window_days
    )
    horizon_days = (
        decision_horizon_days
        if decision_horizon_days is not None
        else cfg.planning_decision_horizon_days
    )

    as_of = as_of_datetime or datetime.now()
    as_of_d = date.today() if as_of_datetime is None else as_of.date()

    # 1. Consumption Statistics
    stats = calculate_demand_statistics(
        db, plant.id, material.id, window_days=stat_days, as_of_date=as_of_d
    )

    # 2. Lead Time Resolution
    lt_res = resolve_lead_time(db, plant.id, material.id, plant_material=pm)

    # 3. Safety Stock V1 Calculation
    ss_res = calculate_safety_stock(
        demand_std_dev=stats.demand_std_dev,
        lead_time_days=lt_res.lead_time_days,
        plant_material=pm,
    )

    # 4. Planning Availability Calculation
    avail_res = calculate_planning_availability(
        db, plant.id, material.id, decision_horizon_days=horizon_days, as_of_date=as_of_d
    )

    # 5. Demand During Lead Time & Reorder Point
    demand_during_lt = round(stats.average_daily_demand * lt_res.lead_time_days, 4)
    reorder_point = round(demand_during_lt + ss_res.safety_stock, 4)

    # 6. Criticality Determination
    ai = avail_res.planning_availability
    status: Literal["CRITICAL", "WARNING", "HEALTHY"]

    if ai < demand_during_lt:
        status = "CRITICAL"
        reason = (
            f"Planning Availability ({ai:.1f} {material.base_uom}) is below demand during "
            f"supplier lead time ({demand_during_lt:.1f} {material.base_uom})."
        )
    elif demand_during_lt <= ai < reorder_point:
        status = "WARNING"
        reason = (
            f"Planning Availability ({ai:.1f} {material.base_uom}) is between demand during "
            f"lead time ({demand_during_lt:.1f} {material.base_uom}) and reorder point "
            f"({reorder_point:.1f} {material.base_uom})."
        )
    else:
        status = "HEALTHY"
        reason = (
            f"Planning Availability ({ai:.1f} {material.base_uom}) meets or exceeds "
            f"reorder point ({reorder_point:.1f} {material.base_uom})."
        )

    return PlanningCalculationResult(
        plant_code=plant.code,
        plant_name=plant.name,
        material_code=material.code,
        material_description=material.description,
        base_uom=material.base_uom,
        as_of_timestamp=as_of,
        average_daily_demand=stats.average_daily_demand,
        demand_std_dev=stats.demand_std_dev,
        observation_days_count=stats.observation_count,
        lead_time_days=lt_res.lead_time_days,
        lead_time_source=lt_res.source,
        service_level_z=ss_res.service_level_z,
        abc_class=ss_res.abc_class,
        safety_stock=ss_res.safety_stock,
        is_safety_stock_overridden=ss_res.is_overridden,
        usable_physical_stock=avail_res.usable_physical_stock,
        reserved_stock_info=avail_res.reserved_stock_info,
        blocked_stock_info=avail_res.blocked_stock_info,
        eligible_incoming_po_qty=avail_res.eligible_incoming_po_qty,
        committed_allocations=avail_res.committed_allocations,
        planning_availability=ai,
        demand_during_lead_time=demand_during_lt,
        reorder_point=reorder_point,
        criticality_status=status,
        explanation=reason,
    )
