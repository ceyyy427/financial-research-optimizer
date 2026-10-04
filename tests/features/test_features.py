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


def test_returns_reject_nonpositive_or_nonintegral_periods():
    for periods in (0, -1, 1.5, True):
        with pytest.raises(ValueError, match="periods"):
            returns(prices(), periods=periods)


def test_momentum_is_lookback_change_and_drawdown_is_peak_relative():
    assert momentum(prices(), window=2).iloc[-1] == pytest.approx(110 / 101 - 1)
    assert drawdown(prices()).iloc[2] == 101 / 102 - 1


def test_features_preserve_empty_and_insufficient_history_as_nan():
    empty = pd.Series(dtype=float)
    assert returns(empty).empty
    assert momentum(empty).empty
    assert drawdown(empty).empty

    short_returns = returns(prices())
    assert volatility(short_returns, window=20, annualization=1).isna().all()
    assert momentum(prices(), window=20).isna().all()


def test_constant_features_are_defined_without_fabricating_variation():
    constant_returns = pd.Series([0.01, 0.01, 0.01, 0.01])
    result = volatility(constant_returns, window=2, annualization=1)
    assert result.iloc[-1] == pytest.approx(0.0)

    matrix = correlation(pd.DataFrame({"a": [1.0, 1.0], "b": [2.0, 3.0]}))
    assert pd.isna(matrix.loc["a", "b"])


def test_price_features_reject_nonfinite_or_nonpositive_prices():
    for invalid in (np.inf, 0.0, -1.0):
        values = pd.Series([100.0, invalid])
        with pytest.raises(ValueError, match="prices"):
            returns(values)


def test_volatility_rejects_invalid_annualization():
    for annualization in (0.0, -1.0, np.inf, np.nan, True):
        with pytest.raises(ValueError, match="annualization"):
            volatility(pd.Series([0.1, 0.2]), window=2, annualization=annualization)


def test_volatility_is_rolling_annualized_std_and_correlation_is_pairwise():
    vol = volatility(returns(prices()), window=3, annualization=1)
    assert np.isfinite(vol.iloc[-1])
    matrix = correlation(pd.DataFrame({"a": prices(), "b": prices() * 2}))
    assert matrix.loc["a", "b"] == 1.0


def test_correlation_requires_two_columns_and_rejects_infinite_values():
    with pytest.raises(ValueError, match="at least two"):
        correlation(pd.DataFrame({"a": [1.0, 2.0]}))
    with pytest.raises(ValueError, match="finite"):
        correlation(pd.DataFrame({"a": [1.0, np.inf], "b": [2.0, 3.0]}))

    empty = correlation(pd.DataFrame({"a": [], "b": []}))
    assert empty.shape == (2, 2)
