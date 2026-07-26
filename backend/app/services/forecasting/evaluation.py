from __future__ import annotations

import math
from typing import NamedTuple

from app.services.forecasting.models import BaseForecastModel


class EvaluationMetrics(NamedTuple):
    mae: float
    rmse: float
    wmape: float


def calculate_metrics(actuals: list[float], predictions: list[float]) -> EvaluationMetrics:
    if not actuals or not predictions or len(actuals) != len(predictions):
        return EvaluationMetrics(mae=0.0, rmse=0.0, wmape=0.0)

    n = len(actuals)
    abs_errors = [abs(act - pred) for act, pred in zip(actuals, predictions, strict=True)]
    mae = sum(abs_errors) / n

    sq_errors = sum((act - pred) ** 2 for act, pred in zip(actuals, predictions, strict=True))
    rmse = math.sqrt(sq_errors / n)

    sum_actuals = sum(actuals)
    wmape = (sum(abs_errors) / sum_actuals) if sum_actuals > 0 else mae

    return EvaluationMetrics(mae=round(mae, 4), rmse=round(rmse, 4), wmape=round(wmape, 4))


def backtest_model(
    model: BaseForecastModel,
    history: list[float],
    test_size: int = 7,
) -> EvaluationMetrics:
    """Evaluates candidate model using chronological train/test split backtesting.
    Ensures zero future-data leakage.
    """
    if len(history) <= test_size:
        return EvaluationMetrics(mae=0.0, rmse=0.0, wmape=0.0)

    train = history[:-test_size]
    test = history[-test_size:]

    predictions = model.fit_predict(train, horizon=test_size)
    return calculate_metrics(test, predictions)
