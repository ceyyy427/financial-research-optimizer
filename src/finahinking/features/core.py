import pandas as pd


def returns(prices: pd.Series, periods: int = 1) -> pd.Series:
    return prices.astype(float).pct_change(periods=periods)


def volatility(returns_series: pd.Series, window: int = 20, annualization: float = 252.0) -> pd.Series:
    if window < 2:
        raise ValueError("window must be at least 2")
    return returns_series.astype(float).rolling(window).std() * annualization**0.5


def momentum(prices: pd.Series, window: int = 20) -> pd.Series:
    if window < 1:
        raise ValueError("window must be positive")
    return prices.astype(float).pct_change(periods=window)


def drawdown(prices: pd.Series) -> pd.Series:
    prices = prices.astype(float)
    return prices / prices.cummax() - 1.0


def correlation(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.shape[1] < 2:
        raise ValueError("correlation requires at least two series")
    return frame.astype(float).corr()
