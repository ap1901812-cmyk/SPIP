from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models.domain import ConsumptionHistory, Material, Plant
from app.services.forecasting import (
    ExponentialSmoothingForecastModel,
    MovingAverageForecastModel,
    NaiveForecastModel,
    backtest_model,
    calculate_metrics,
    generate_demand_forecast,
)


def _seed_forecasting_test_data(db: Session) -> tuple[Plant, Material]:
    plant = Plant(code="PLANT-FC", name="Forecast Test Plant")
    material = Material(code="MAT-FC", description="Forecast Test Material", base_uom="KG")
    db.add_all([plant, material])
    db.commit()
    return plant, material


def test_forecast_candidate_models_deterministic() -> None:
    history = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0]

    naive = NaiveForecastModel()
    assert naive.fit_predict(history, horizon=3) == [22.0, 22.0, 22.0]

    ma = MovingAverageForecastModel(window=3)
    assert ma.fit_predict(history, horizon=3) == [20.0, 20.0, 20.0]

    es = ExponentialSmoothingForecastModel(alpha=0.5)
    preds = es.fit_predict(history, horizon=3)
    assert len(preds) == 3
    assert all(p > 0 for p in preds)


def test_backtesting_and_evaluation_metrics() -> None:
    actuals = [10.0, 20.0, 30.0]
    preds = [12.0, 18.0, 33.0]

    metrics = calculate_metrics(actuals, preds)
    # MAE = (|2| + |2| + |3|)/3 = 7/3 = 2.3333
    assert metrics.mae == 2.3333
    assert metrics.rmse > 0.0
    assert metrics.wmape > 0.0

    history = [10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0]
    bt_metrics = backtest_model(MovingAverageForecastModel(3), history, test_size=3)
    assert bt_metrics.mae >= 0.0


def test_insufficient_history_fallback(db_session: Session) -> None:
    plant, material = _seed_forecasting_test_data(db_session)
    today = date.today()

    # Seed only 3 days of consumption (< 5 observations threshold)
    for i in range(3):
        db_session.add(
            ConsumptionHistory(
                plant_id=plant.id,
                material_id=material.id,
                consumption_date=today - timedelta(days=i),
                quantity=100.0,
                uom="KG",
            )
        )
    db_session.commit()

    res = generate_demand_forecast(
        db_session, plant.code, material.code, horizon_days=5, as_of_date=today
    )
    assert res.is_fallback is True
    assert "Insufficient historical consumption records" in (res.fallback_reason or "")
    assert res.forecast_horizon_days == 5
    assert len(res.point_forecasts) == 5
    assert res.total_forecasted_demand == 500.0


def test_normal_forecast_generation_with_model_selection(db_session: Session) -> None:
    plant, material = _seed_forecasting_test_data(db_session)
    today = date.today()

    # Seed 20 days of historical demand
    for i in range(20, 0, -1):
        db_session.add(
            ConsumptionHistory(
                plant_id=plant.id,
                material_id=material.id,
                consumption_date=today - timedelta(days=i),
                quantity=50.0 + i,
                uom="KG",
            )
        )
    db_session.commit()

    res = generate_demand_forecast(
        db_session, plant.code, material.code, horizon_days=12, as_of_date=today
    )

    assert res.is_fallback is False
    assert res.selected_model in [
        "MOVING_AVERAGE_7D",
        "MOVING_AVERAGE_14D",
        "EXP_SMOOTHING_A30",
        "NAIVE_LAST_VALUE",
    ]
    assert len(res.point_forecasts) == 12
    assert res.point_forecasts[0].forecast_date == today + timedelta(days=1)
    assert res.point_forecasts[-1].forecast_date == today + timedelta(days=12)
