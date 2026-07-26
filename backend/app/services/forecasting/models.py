from __future__ import annotations

from abc import ABC, abstractmethod


class BaseForecastModel(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def fit_predict(self, history: list[float], horizon: int) -> list[float]:
        pass


class NaiveForecastModel(BaseForecastModel):
    @property
    def name(self) -> str:
        return "NAIVE_LAST_VALUE"

    def fit_predict(self, history: list[float], horizon: int) -> list[float]:
        if not history:
            return [0.0] * horizon
        val = max(0.0, float(history[-1]))
        return [round(val, 4)] * horizon


class MovingAverageForecastModel(BaseForecastModel):
    def __init__(self, window: int = 7) -> None:
        self.window = window

    @property
    def name(self) -> str:
        return f"MOVING_AVERAGE_{self.window}D"

    def fit_predict(self, history: list[float], horizon: int) -> list[float]:
        if not history:
            return [0.0] * horizon
        recent = history[-self.window :] if len(history) >= self.window else history
        avg = max(0.0, sum(recent) / len(recent))
        return [round(avg, 4)] * horizon


class ExponentialSmoothingForecastModel(BaseForecastModel):
    def __init__(self, alpha: float = 0.3) -> None:
        self.alpha = alpha

    @property
    def name(self) -> str:
        return f"EXP_SMOOTHING_A{int(self.alpha * 100)}"

    def fit_predict(self, history: list[float], horizon: int) -> list[float]:
        if not history:
            return [0.0] * horizon
        s = float(history[0])
        for y in history[1:]:
            s = self.alpha * float(y) + (1 - self.alpha) * s
        s = max(0.0, s)
        return [round(s, 4)] * horizon
