from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.db.models.domain import Material, Plant, PlantMaterial
from app.schemas.planning import PlanningCalculationResult
from app.services.planning.consumption_intelligence import analyze_consumption_intelligence
from app.services.planning.inventory_intelligence import analyze_inventory_intelligence
from app.services.planning.lead_time import resolve_dual_lead_time
from app.services.planning.safety_stock import calculate_dual_safety_stock


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
    """Evaluates material planning decision rules according to RMPM statistical planning methodology.

    Sequence:
    1. Consumption Intelligence (D_avg, sigma_d, Trend, CV)
    2. Inventory Intelligence (Stock, PO, Gate Entry, AI, DOI)
    3. RMPM Dual Lead Times (LT-1, LT-2)
    4. RMPM Dual Safety Stocks (SS-1, SS-2)
    5. RMPM Triggers (Trigger-1, Trigger-2)
    6. RMPM Material Status Decision Tree (CRITICAL, REORDER_REQUIRED, LOW_STOCK, HEALTHY)
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

    # 1. Consumption Intelligence Engine
    c_intel = analyze_consumption_intelligence(
        db, plant.id, material.id, window_days=stat_days, as_of_date=as_of_d
    )

    # 2. Inventory Intelligence Engine
    inv_intel = analyze_inventory_intelligence(
        db,
        plant.id,
        material.id,
        average_daily_demand=c_intel.average_daily_demand,
        decision_horizon_days=horizon_days,
        as_of_date=as_of_d,
    )

    # 3. RMPM Dual Lead Time Resolution
    lt_res = resolve_dual_lead_time(db, plant.id, material.id, plant_material=pm)

    # 4. RMPM Dual Safety Stock Calculation
    ss_res = calculate_dual_safety_stock(
        demand_std_dev=c_intel.demand_std_dev,
        lead_time_1=lt_res.lead_time_1,
        lead_time_2=lt_res.lead_time_2,
        plant_material=pm,
    )

    # 5. RMPM Reorder Triggers
    d_avg = c_intel.average_daily_demand
    demand_during_lt1 = round(d_avg * lt_res.lead_time_1, 4)
    demand_during_lt2 = round(d_avg * lt_res.lead_time_2, 4)

    trigger_1 = round(demand_during_lt1 + ss_res.safety_stock_1, 4)
    trigger_2 = round(demand_during_lt2 + ss_res.safety_stock_2, 4)

    # 6. Requirement Resolution Engine
    from app.services.forecasting.engine import generate_demand_forecast
    from app.services.planning.requirement_resolution import resolve_planning_requirement

    try:
        fc_res = generate_demand_forecast(db, plant.code, material.code, horizon_days=horizon_days)
        fc_daily = fc_res.average_forecasted_daily_demand
    except Exception:
        fc_daily = 0.0

    req_res = resolve_planning_requirement(
        db,
        plant_id=plant.id,
        material_id=material.id,
        forecast_daily_qty=fc_daily,
        historical_daily_qty=c_intel.average_daily_demand,
    )

    # 7. RMPM Material Status Decision Tree
    ai = inv_intel.planning_available_inventory
    rmpm_status: str
    legacy_status: Literal["CRITICAL", "WARNING", "HEALTHY"]
    explanation: str

    # 4-tier RMPM Status
    if ai < ss_res.safety_stock_2:
        rmpm_status = "CRITICAL"
        explanation = (
            f"CRITICAL: Available Stock ({ai:.1f} {material.base_uom}) has breached Safety Stock 2 "
            f"({ss_res.safety_stock_2:.1f} {material.base_uom}). Emergency replenishment required immediately."
        )
    elif ss_res.safety_stock_2 <= ai < trigger_2:
        rmpm_status = "REORDER_REQUIRED"
        explanation = (
            f"REORDER REQUIRED: Available Stock ({ai:.1f} {material.base_uom}) is below Trigger 2 "
            f"({trigger_2:.1f} {material.base_uom}). Regular replenishment order placement required."
        )
    elif trigger_2 <= ai < trigger_1:
        rmpm_status = "LOW_STOCK"
        explanation = (
            f"LOW STOCK: Available Stock ({ai:.1f} {material.base_uom}) is below Trigger 1 "
            f"({trigger_1:.1f} {material.base_uom}). Monitor supply cycle."
        )
    else:
        rmpm_status = "HEALTHY"
        explanation = (
            f"HEALTHY: Available Stock ({ai:.1f} {material.base_uom}) meets or exceeds Trigger 1 "
            f"({trigger_1:.1f} {material.base_uom}). Stock level is healthy."
        )

    # Legacy 3-tier Criticality Status (for 100% backward compatibility)
    if ai < demand_during_lt1:
        legacy_status = "CRITICAL"
    elif demand_during_lt1 <= ai < trigger_1:
        legacy_status = "WARNING"
    else:
        legacy_status = "HEALTHY"

    return PlanningCalculationResult(
        plant_code=plant.code,
        plant_name=plant.name,
        material_code=material.code,
        material_description=material.description,
        base_uom=material.base_uom,
        as_of_timestamp=as_of,
        average_daily_demand=c_intel.average_daily_demand,
        demand_std_dev=c_intel.demand_std_dev,
        observation_days_count=c_intel.observation_days_count,
        consumption_trend=c_intel.consumption_trend,
        consumption_variability=c_intel.consumption_variability,
        lead_time_1=lt_res.lead_time_1,
        lead_time_2=lt_res.lead_time_2,
        lead_time_days=lt_res.lead_time_1,
        lead_time_source=lt_res.source_lt1,
        service_level_z=ss_res.service_level_z,
        abc_class=ss_res.abc_class,
        safety_stock_1=ss_res.safety_stock_1,
        safety_stock_2=ss_res.safety_stock_2,
        safety_stock=ss_res.safety_stock_1,
        is_safety_stock_overridden=ss_res.is_overridden,
        usable_physical_stock=inv_intel.usable_physical_stock,
        reserved_stock_info=inv_intel.reserved_stock,
        blocked_stock_info=inv_intel.blocked_stock,
        eligible_incoming_po_qty=inv_intel.incoming_inventory,
        committed_allocations=inv_intel.committed_allocations,
        planning_availability=ai,
        days_of_inventory=inv_intel.days_of_inventory,
        trigger_1=trigger_1,
        trigger_2=trigger_2,
        demand_during_lead_time=demand_during_lt1,
        reorder_point=trigger_1,
        final_planning_requirement=req_res.final_planning_requirement,
        requirement_source=req_res.requirement_source,
        requirement_resolution_reason=req_res.resolution_reason,
        rmpm_material_status=rmpm_status,
        criticality_status=legacy_status,
        explanation=explanation,
    )
