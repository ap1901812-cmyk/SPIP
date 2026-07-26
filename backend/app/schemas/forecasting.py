from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ForecastDayPoint(BaseModel):
    day_offset: int = Field(..., ge=1)
    forecast_date: date
    forecasted_quantity: float = Field(..., ge=0.0)
    uom: str


class ForecastCalculationResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plant_code: str
    material_code: str
    base_uom: str
    generated_at: datetime
    forecast_horizon_days: int
    historical_window_days: int
    selected_model: str
    evaluation_metric_name: str
    evaluation_metric_value: float
    is_fallback: bool
    fallback_reason: str | None = None
    total_forecasted_demand: float
    average_forecasted_daily_demand: float
    point_forecasts: list[ForecastDayPoint]
