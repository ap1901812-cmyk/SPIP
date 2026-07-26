from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models.domain import ConsumptionHistory, Material, Plant
from app.schemas.forecasting import ForecastCalculationResult, ForecastDayPoint
from app.services.forecasting.evaluation import backtest_model
from app.services.forecasting.models import (
    BaseForecastModel,
    ExponentialSmoothingForecastModel,
    MovingAverageForecastModel,
    NaiveForecastModel,
)


class ForecastingEngineError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__("FORECASTING_ENGINE_ERROR", message, 404)


def generate_demand_forecast(
    db: Session,
    plant_code: str,
    material_code: str,
    horizon_days: int = 12,
    as_of_date: date | None = None,
) -> ForecastCalculationResult:
    """Generates time-aware demand forecast using backtested candidate model selection
    or deterministic fallback for insufficient history.
    """
    plant = db.query(Plant).filter(Plant.code == plant_code).first()
    if not plant:
        raise ForecastingEngineError(f"Plant with code '{plant_code}' not found.")

    material = db.query(Material).filter(Material.code == material_code).first()
    if not material:
        raise ForecastingEngineError(f"Material with code '{material_code}' not found.")

    ref_date = as_of_date or date.today()
    window_start = ref_date - timedelta(days=90)

    # Strictly chronological historical consumption
    records = (
        db.query(ConsumptionHistory)
        .filter(
            ConsumptionHistory.plant_id == plant.id,
            ConsumptionHistory.material_id == material.id,
            ConsumptionHistory.consumption_date >= window_start,
            ConsumptionHistory.consumption_date <= ref_date,
        )
        .order_by(ConsumptionHistory.consumption_date.asc())
        .all()
    )

    history_quantities = [float(r.quantity) for r in records if r.quantity >= 0.0]
    num_obs = len(history_quantities)

    candidates: list[BaseForecastModel] = [
        MovingAverageForecastModel(window=7),
        MovingAverageForecastModel(window=14),
        ExponentialSmoothingForecastModel(alpha=0.3),
        NaiveForecastModel(),
    ]

    selected_model: BaseForecastModel
    best_wmape: float = 0.0
    is_fallback: bool = False
    fallback_reason: str | None = None

    # Insufficient history fallback check
    if num_obs < 5:
        is_fallback = True
        fallback_reason = "Insufficient historical consumption records (< 5 observations)"
        selected_model = MovingAverageForecastModel(window=7)

        # Baseline fallback mean calculation
        if num_obs > 0:
            avg_val = sum(history_quantities) / num_obs
            predictions = [round(max(0.0, avg_val), 4)] * horizon_days
        else:
            predictions = [0.0] * horizon_days
    else:
        # Backtest candidate model selection on holdout period
        best_score = float("inf")
        best_model = candidates[0]

        for cand in candidates:
            metrics = backtest_model(cand, history_quantities, test_size=min(7, num_obs // 2))
            if metrics.wmape < best_score:
                best_score = metrics.wmape
                best_model = cand

        selected_model = best_model
        best_wmape = round(best_score, 4)
        predictions = selected_model.fit_predict(history_quantities, horizon=horizon_days)

    point_forecasts: list[ForecastDayPoint] = []
    for day_idx, qty in enumerate(predictions, start=1):
        f_date = ref_date + timedelta(days=day_idx)
        point_forecasts.append(
            ForecastDayPoint(
                day_offset=day_idx,
                forecast_date=f_date,
                forecasted_quantity=qty,
                uom=material.base_uom,
            )
        )

    total_demand = round(sum(predictions), 4)
    avg_daily_demand = round(total_demand / horizon_days, 4) if horizon_days > 0 else 0.0

    return ForecastCalculationResult(
        plant_code=plant.code,
        material_code=material.code,
        base_uom=material.base_uom,
        generated_at=datetime.now(UTC),
        forecast_horizon_days=horizon_days,
        historical_window_days=90,
        selected_model=selected_model.name,
        evaluation_metric_name="WMAPE",
        evaluation_metric_value=best_wmape,
        is_fallback=is_fallback,
        fallback_reason=fallback_reason,
        total_forecasted_demand=total_demand,
        average_forecasted_daily_demand=avg_daily_demand,
        point_forecasts=point_forecasts,
    )
