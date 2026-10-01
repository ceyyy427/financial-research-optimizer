import numpy as np
import pandas as pd
import pytest

from finahinking.features.core import correlation, drawdown, momentum, returns, volatility


def prices():
    return pd.Series([100, 102, 101, 105, 110], index=pd.date_range("2024-01-01", periods=5, freq="D"), name="close")


def test_returns_are_simple_percentage_changes():
    result = returns(prices())
    assert result.iloc[1] == pytest.approx(0.02)
    assert pd.isna(result.iloc[0])


def test_momentum_is_lookback_change_and_drawdown_is_peak_relative():
    assert momentum(prices(), window=2).iloc[-1] == pytest.approx(110 / 101 - 1)
    assert drawdown(prices()).iloc[2] == 101 / 102 - 1


def test_volatility_is_rolling_annualized_std_and_correlation_is_pairwise():
    vol = volatility(returns(prices()), window=3, annualization=1)
    assert np.isfinite(vol.iloc[-1])
    matrix = correlation(pd.DataFrame({"a": prices(), "b": prices() * 2}))
    assert matrix.loc["a", "b"] == 1.0
