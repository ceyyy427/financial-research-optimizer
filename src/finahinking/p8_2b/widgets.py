"""Allow-listed deterministic educational calculations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, stdev
from typing import Any

_KINDS = {"volatility", "sharpe", "ols", "momentum", "oos_split"}


def _series(values: Any, label: str, minimum: int = 2) -> list[float]:
    if not isinstance(values, (list, tuple)) or not minimum <= len(values) <= 10_000:
        raise ValueError(f"{label} must contain {minimum} to 10000 values")
    result = [float(value) for value in values]
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{label} values must be finite")
    return result


@dataclass(frozen=True)
class WidgetSpec:
    widget_id: str
    kind: str
    parameters: dict[str, object]

    def __post_init__(self) -> None:
        if not self.widget_id.strip() or any(char.isspace() for char in self.widget_id):
            raise ValueError("widget_id is invalid")
        if self.kind not in _KINDS:
            raise ValueError("widget kind is invalid")
        if not isinstance(self.parameters, dict):
            raise TypeError("parameters must be an object")


@dataclass(frozen=True)
class WidgetResult:
    widget_id: str
    kind: str
    values: dict[str, object]
    status: str = "PASS"

    def to_dict(self) -> dict[str, object]:
        return {"widget_id": self.widget_id, "kind": self.kind, "values": self.values, "status": self.status}


def _annualization(parameters: dict[str, object]) -> float:
    value = float(parameters.get("annualization", 252))
    if not 1 <= value <= 366 or not math.isfinite(value):
        raise ValueError("annualization is out of bounds")
    return value


def _volatility(spec: WidgetSpec) -> WidgetResult:
    returns = _series(spec.parameters.get("returns"), "returns")
    annualization = _annualization(spec.parameters)
    daily = stdev(returns)
    return WidgetResult(spec.widget_id, spec.kind, {"observations": len(returns), "daily_volatility": daily, "annualized_volatility": daily * math.sqrt(annualization), "annualization": annualization})


def _sharpe(spec: WidgetSpec) -> WidgetResult:
    returns = _series(spec.parameters.get("returns"), "returns")
    risk_free = float(spec.parameters.get("risk_free", 0.0))
    if not math.isfinite(risk_free):
        raise ValueError("risk_free must be finite")
    annualization = _annualization(spec.parameters)
    excess = [value - risk_free for value in returns]
    deviation = stdev(excess)
    if deviation == 0:
        raise ValueError("sharpe volatility cannot be zero")
    return WidgetResult(spec.widget_id, spec.kind, {"observations": len(returns), "mean_excess_return": mean(excess), "volatility": deviation, "sharpe": mean(excess) / deviation * math.sqrt(annualization), "annualization": annualization})


def _ols(spec: WidgetSpec) -> WidgetResult:
    x, y = _series(spec.parameters.get("x"), "x"), _series(spec.parameters.get("y"), "y")
    if len(x) != len(y) or len(x) < 2:
        raise ValueError("x and y must have equal length")
    x_mean, y_mean = mean(x), mean(y)
    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        raise ValueError("x variance cannot be zero")
    beta = sum((x_value - x_mean) * (y_value - y_mean) for x_value, y_value in zip(x, y)) / denominator
    alpha = y_mean - beta * x_mean
    residuals = [actual - (alpha + beta * value) for value, actual in zip(x, y)]
    return WidgetResult(spec.widget_id, spec.kind, {"observations": len(x), "alpha": alpha, "beta": beta, "residuals": residuals})


def _momentum(spec: WidgetSpec) -> WidgetResult:
    prices = _series(spec.parameters.get("prices"), "prices")
    lookback = int(spec.parameters.get("lookback", 20))
    if not 1 <= lookback < len(prices):
        raise ValueError("lookback is out of bounds")
    start, end = prices[-lookback - 1], prices[-1]
    if start == 0:
        raise ValueError("starting price cannot be zero")
    return WidgetResult(spec.widget_id, spec.kind, {"lookback": lookback, "start_price": start, "end_price": end, "return": end / start - 1})


def _oos_split(spec: WidgetSpec) -> WidgetResult:
    values = _series(spec.parameters.get("values"), "values", 2)
    ratio = float(spec.parameters.get("train_ratio", 0.7))
    if not math.isfinite(ratio) or not 0.5 <= ratio <= 0.8:
        raise ValueError("train_ratio must be between 0.5 and 0.8")
    split = max(1, min(len(values) - 1, int(len(values) * ratio)))
    return WidgetResult(spec.widget_id, spec.kind, {"train": values[:split], "oos": values[split:], "train_ratio": ratio, "split_index": split})


def run_widget(spec: WidgetSpec) -> WidgetResult:
    return {"volatility": _volatility, "sharpe": _sharpe, "ols": _ols, "momentum": _momentum, "oos_split": _oos_split}[spec.kind](spec)
