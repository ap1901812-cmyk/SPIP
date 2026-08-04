from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models.domain import Material, Plant


class ResolvedRequirementResult(BaseModel):
    plant_code: str
    material_code: str
    final_planning_requirement: float
    requirement_source: str
    resolution_reason: str
    resolution_timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_values: dict[str, float] = Field(default_factory=dict)


def resolve_planning_requirement(
    db: Session,
    plant_id: int,
    material_id: int,
    forecast_daily_qty: float = 0.0,
    historical_daily_qty: float = 0.0,
    ibp_daily_qty: float | None = None,
    monthly_schedule_qty: float | None = None,
) -> ResolvedRequirementResult:
    """Requirement Resolution Engine creating one final planning requirement from multiple business demand sources.

    Hierarchy & Conflict Resolution Rules:
    1. Priority 1: IBP Daily Requirement (if uploaded & active)
    2. Priority 2: Monthly Requirement Schedule (Monthly Demand / 22 working days)
    3. Priority 3: Statistical Forecast (Moving Average / Backtested model output)
    4. Priority 4: Historical Consumption (D_avg fallback)
    """
    plant = db.query(Plant).filter(Plant.id == plant_id).first()
    material = db.query(Material).filter(Material.id == material_id).first()

    plant_code = plant.code if plant else str(plant_id)
    material_code = material.code if material else str(material_id)

    input_map: dict[str, float] = {
        "historical_daily_consumption": round(historical_daily_qty, 4),
        "statistical_forecast": round(forecast_daily_qty, 4),
    }

    if ibp_daily_qty is not None:
        input_map["ibp_daily_requirement"] = round(ibp_daily_qty, 4)

    if monthly_schedule_qty is not None:
        input_map["monthly_schedule_daily"] = round(monthly_schedule_qty / 22.0, 4)

    # 1. Check IBP Daily
    if ibp_daily_qty is not None and ibp_daily_qty > 0:
        return ResolvedRequirementResult(
            plant_code=plant_code,
            material_code=material_code,
            final_planning_requirement=round(ibp_daily_qty, 4),
            requirement_source="IBP_DAILY",
            resolution_reason=f"Selected active IBP Daily Requirement ({ibp_daily_qty:.2f} base UOM/day) over lower priority demand sources.",
            input_values=input_map,
        )

    # 2. Check Monthly Schedule
    if monthly_schedule_qty is not None and monthly_schedule_qty > 0:
        daily_monthly = round(monthly_schedule_qty / 22.0, 4)
        return ResolvedRequirementResult(
            plant_code=plant_code,
            material_code=material_code,
            final_planning_requirement=daily_monthly,
            requirement_source="MONTHLY_SCHEDULE",
            resolution_reason=f"Selected active Monthly Requirement schedule ({monthly_schedule_qty:.1f} / 22 working days = {daily_monthly:.2f} base UOM/day).",
            input_values=input_map,
        )

    # 3. Check Statistical Forecast
    if forecast_daily_qty > 0:
        return ResolvedRequirementResult(
            plant_code=plant_code,
            material_code=material_code,
            final_planning_requirement=round(forecast_daily_qty, 4),
            requirement_source="STATISTICAL_FORECAST",
            resolution_reason=f"Selected Statistical Moving Average Forecast ({forecast_daily_qty:.2f} base UOM/day).",
            input_values=input_map,
        )

    # 4. Fallback: Historical Consumption (D_avg)
    fallback_qty = round(max(0.0, historical_daily_qty), 4)
    return ResolvedRequirementResult(
        plant_code=plant_code,
        material_code=material_code,
        final_planning_requirement=fallback_qty,
        requirement_source="HISTORICAL_CONSUMPTION",
        resolution_reason=f"Selected Historical Average Daily Consumption ({fallback_qty:.2f} base UOM/day) as baseline fallback.",
        input_values=input_map,
    )
