from __future__ import annotations

import math
from datetime import date, timedelta
from typing import NamedTuple

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.domain import ConsumptionHistory


class ConsumptionIntelligenceResult(BaseModel):
    plant_id: int
    material_id: int
    daily_consumption: float = 0.0
    weekly_consumption: float = 0.0
    monthly_consumption: float = 0.0
    average_daily_demand: float = 0.0
    demand_std_dev: float = 0.0
    observation_days_count: int = 0
    consumption_trend: str = "STABLE"
    consumption_variability: float = 0.0


def analyze_consumption_intelligence(
    db: Session,
    plant_id: int,
    material_id: int,
    window_days: int | None = None,
    as_of_date: date | None = None,
) -> ConsumptionIntelligenceResult:
    """Consumes historical consumption records and evaluates daily, weekly, monthly consumption,

    rolling D_avg, demand_std_dev, consumption trend, and coefficient of variability.
    """
    cfg = get_settings()
    days = window_days if window_days is not None else cfg.planning_statistics_window_days
    ref_date = as_of_date or date.today()
    start_date = ref_date - timedelta(days=days)

    records = (
        db.query(ConsumptionHistory)
        .filter(
            ConsumptionHistory.plant_id == plant_id,
            ConsumptionHistory.material_id == material_id,
            ConsumptionHistory.consumption_date >= start_date,
            ConsumptionHistory.consumption_date <= ref_date,
        )
        .order_by(ConsumptionHistory.consumption_date.asc())
        .all()
    )

    if not records:
        return ConsumptionIntelligenceResult(plant_id=plant_id, material_id=material_id)

    # Filter non-negative quantities
    valid_records = [r for r in records if r.quantity >= 0.0]
    if not valid_records:
        return ConsumptionIntelligenceResult(plant_id=plant_id, material_id=material_id)

    quantities = [r.quantity for r in valid_records]
    n = len(quantities)

    mean_demand = sum(quantities) / n

    if n == 1:
        std_dev = 0.0
    else:
        variance = sum((x - mean_demand) ** 2 for x in quantities) / n
        std_dev = math.sqrt(variance)

    # Weekly & Monthly Aggregations
    week_start = ref_date - timedelta(days=7)
    month_start = ref_date - timedelta(days=30)

    weekly_qty = sum(r.quantity for r in valid_records if r.consumption_date >= week_start)
    monthly_qty = sum(r.quantity for r in valid_records if r.consumption_date >= month_start)
    latest_daily = valid_records[-1].quantity if valid_records else 0.0

    # Trend calculation (comparing second half mean vs first half mean)
    trend = "STABLE"
    if n >= 4:
        half = n // 2
        first_half_mean = sum(quantities[:half]) / half
        second_half_mean = sum(quantities[half:]) / (n - half)

        if second_half_mean > first_half_mean * 1.15:
            trend = "INCREASING"
        elif second_half_mean < first_half_mean * 0.85:
            trend = "DECREASING"

    # Variability (CV = std_dev / mean)
    variability = round(std_dev / mean_demand, 4) if mean_demand > 0 else 0.0

    return ConsumptionIntelligenceResult(
        plant_id=plant_id,
        material_id=material_id,
        daily_consumption=round(latest_daily, 4),
        weekly_consumption=round(weekly_qty, 4),
        monthly_consumption=round(monthly_qty, 4),
        average_daily_demand=round(mean_demand, 4),
        demand_std_dev=round(std_dev, 4),
        observation_days_count=n,
        consumption_trend=trend,
        consumption_variability=variability,
    )
