import numbers
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from finahinking.features.core import momentum


@dataclass(frozen=True)
class FactorDefinition:
    name: str
    definition: str
    explanation: str
    limitations: str
    compute: callable
    metadata: Any | None = None
    health: Any | None = None


def momentum_factor(window: int = 20) -> FactorDefinition:
    if isinstance(window, bool) or not isinstance(window, numbers.Integral) or window < 1:
        raise ValueError("window must be a positive integer")
    window = int(window)
    return FactorDefinition(
        name=f"momentum_{window}d",
        definition=f"Percentage change over the previous {window} observations.",
        explanation="Ranks observations by trailing price strength.",
        limitations="Must be shifted before forecasting to avoid look-ahead bias and leakage; sensitive to regime changes, costs, survivorship bias, and multiple testing.",
        compute=lambda prices: momentum(prices, window),
    )


def evaluate_factor(
    factor_values: pd.Series,
    forward_returns: pd.Series,
    *,
    shift_periods: int = 1,
) -> dict[str, float]:
    if (
        isinstance(shift_periods, bool)
        or not isinstance(shift_periods, numbers.Integral)
        or shift_periods < 0
    ):
        raise ValueError("shift_periods must be a non-negative integer")
    if not factor_values.index.is_unique or not forward_returns.index.is_unique:
        raise ValueError("factor and forward-return indexes must be unique")
    if not factor_values.index.equals(forward_returns.index):
        raise ValueError("factor and forward-return series must use the same index")
    if not factor_values.index.is_monotonic_increasing or not forward_returns.index.is_monotonic_increasing:
        raise ValueError("factor and forward-return indexes must be increasing")
    factor_numeric = factor_values.astype(float)
    forward_numeric = forward_returns.astype(float)
    if np.isinf(factor_numeric.to_numpy()).any() or np.isinf(forward_numeric.to_numpy()).any():
        raise ValueError("factor and forward-return values must be finite or missing")
    shifted_factor = factor_numeric.shift(int(shift_periods))
    aligned = pd.concat([shifted_factor.rename("factor"), forward_numeric.rename("forward")], axis=1).dropna()
    coverage = len(aligned) / len(factor_values) if len(factor_values) else 0.0
    if len(aligned) < 2 or aligned["factor"].nunique() < 2 or aligned["forward"].nunique() < 2:
        ic = float("nan")
    else:
        ic = aligned["factor"].corr(aligned["forward"])
    return {"coverage": float(coverage), "information_coefficient": float(ic)}
