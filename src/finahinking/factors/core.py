from dataclasses import dataclass

import pandas as pd

from finahinking.features.core import momentum


@dataclass(frozen=True)
class FactorDefinition:
    name: str
    definition: str
    explanation: str
    limitations: str
    compute: callable


def momentum_factor(window: int = 20) -> FactorDefinition:
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
    if shift_periods < 0:
        raise ValueError("shift_periods must be non-negative")
    shifted_factor = factor_values.shift(shift_periods)
    aligned = pd.concat([shifted_factor.rename("factor"), forward_returns.rename("forward")], axis=1).dropna()
    coverage = len(aligned) / len(factor_values) if len(factor_values) else 0.0
    if len(aligned) < 2 or aligned["factor"].nunique() < 2 or aligned["forward"].nunique() < 2:
        ic = float("nan")
    else:
        ic = aligned["factor"].corr(aligned["forward"])
    return {"coverage": float(coverage), "information_coefficient": float(ic)}
