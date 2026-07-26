from __future__ import annotations

import math
from datetime import date, timedelta
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.domain import ConsumptionHistory


class DemandStatistics(NamedTuple):
    average_daily_demand: float
    demand_std_dev: float
    observation_count: int


def calculate_demand_statistics(
    db: Session,
    plant_id: int,
    material_id: int,
    window_days: int | None = None,
    as_of_date: date | None = None,
) -> DemandStatistics:
    """Calculates average daily demand and population demand standard deviation
    from rolling historical consumption observations using configured window days.
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
        return DemandStatistics(average_daily_demand=0.0, demand_std_dev=0.0, observation_count=0)

    quantities = [r.quantity for r in records if r.quantity >= 0.0]
    n = len(quantities)
    if n == 0:
        return DemandStatistics(average_daily_demand=0.0, demand_std_dev=0.0, observation_count=0)

    mean_demand = sum(quantities) / n

    if n == 1:
        std_dev = 0.0
    else:
        variance = sum((x - mean_demand) ** 2 for x in quantities) / n
        std_dev = math.sqrt(variance)

    return DemandStatistics(
        average_daily_demand=round(mean_demand, 4),
        demand_std_dev=round(std_dev, 4),
        observation_count=n,
    )
