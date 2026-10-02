import numbers

import numpy as np
import pandas as pd


def _positive_integer(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, numbers.Integral) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _price_series(prices: pd.Series) -> pd.Series:
    values = prices.astype(float)
    observed = values.dropna()
    if not np.isfinite(observed.to_numpy()).all() or (observed <= 0).any():
        raise ValueError("prices must be finite and strictly positive")
    return values


def returns(prices: pd.Series, periods: int = 1) -> pd.Series:
    periods = _positive_integer(periods, "periods")
    return _price_series(prices).pct_change(periods=periods)


def volatility(returns_series: pd.Series, window: int = 20, annualization: float = 252.0) -> pd.Series:
    if isinstance(window, bool) or not isinstance(window, numbers.Integral) or window < 2:
        raise ValueError("window must be at least 2")
    if (
        isinstance(annualization, bool)
        or not isinstance(annualization, numbers.Real)
        or not np.isfinite(annualization)
        or annualization <= 0
    ):
        raise ValueError("annualization must be a positive finite number")
    values = returns_series.astype(float)
    if np.isinf(values.to_numpy()).any():
        raise ValueError("returns must be finite or missing")
    return values.rolling(int(window)).std() * float(annualization) ** 0.5


def momentum(prices: pd.Series, window: int = 20) -> pd.Series:
    window = _positive_integer(window, "window")
    return _price_series(prices).pct_change(periods=window)


def drawdown(prices: pd.Series) -> pd.Series:
    values = _price_series(prices)
    return values / values.cummax() - 1.0


def correlation(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.shape[1] < 2:
        raise ValueError("correlation requires at least two series")
    values = frame.astype(float)
    if np.isinf(values.to_numpy()).any():
        raise ValueError("correlation inputs must be finite or missing")
    return values.corr()
