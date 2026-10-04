"""Pure historical risk metrics with explicit undefined-value behavior."""

from __future__ import annotations

import math

import pandas as pd


def _clean(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").replace([float("inf"), float("-inf")], pd.NA)
    return numeric.dropna().astype(float)


def maximum_drawdown(equity: pd.Series) -> float | None:
    values = _clean(equity)
    if values.empty:
        return None
    if (values <= 0).any():
        return None
    return float((values / values.cummax() - 1.0).min())


def downside_deviation(returns: pd.Series, annualization: int = 252) -> float | None:
    values = _clean(returns)
    negatives = values[values < 0]
    if len(negatives) < 2:
        return None
    if not isinstance(annualization, int) or annualization < 1:
        raise ValueError("annualization must be a positive integer")
    return float(math.sqrt((negatives.pow(2).mean()) * annualization))


def value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float | None:
    values = _clean(returns)
    if len(values) < 2:
        return None
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    return float(max(0.0, -values.quantile(1.0 - confidence)))


def conditional_value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float | None:
    values = _clean(returns)
    if len(values) < 2:
        return None
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    threshold = values.quantile(1.0 - confidence)
    tail = values[values <= threshold]
    if tail.empty:
        return None
    return float(max(0.0, -tail.mean()))
