import numpy as np
import pandas as pd
import pytest

from finahinking.factors.core import evaluate_factor, momentum_factor


def test_momentum_factor_contains_definition_and_limitations():
    factor = momentum_factor(window=2)
    assert factor.name == "momentum_2d"
    assert factor.definition
    assert factor.explanation
    assert "look-ahead" in factor.limitations.lower()
    assert callable(factor.compute)


def test_momentum_factor_rejects_invalid_windows():
    for window in (0, -1, 1.5, True):
        with pytest.raises(ValueError, match="window"):
            momentum_factor(window=window)


def test_evaluate_factor_reports_coverage_and_information_coefficient():
    factor_values = pd.Series([0.1, 0.2, 0.3, 0.4], index=pd.date_range("2024-01-01", periods=4))
    forward = pd.Series([0.0, 0.1, 0.2, 0.3], index=factor_values.index)
    result = evaluate_factor(factor_values, forward)
    assert result["coverage"] == 0.75
    assert result["information_coefficient"] == 1.0


def test_evaluate_factor_marks_constant_inputs_as_undefined_without_crashing():
    values = pd.Series(1.0, index=pd.date_range("2024-01-01", periods=3))
    forward = pd.Series([0.1, 0.2, 0.3], index=values.index)
    result = evaluate_factor(values, forward)
    assert result["coverage"] == 2 / 3
    assert pd.isna(result["information_coefficient"])


def test_evaluate_factor_applies_the_default_lag_to_nonmonotonic_values():
    index = pd.date_range("2024-01-01", periods=4)
    factor_values = pd.Series([1.0, 2.0, 4.0, 3.0], index=index)
    forward = pd.Series([0.0, 1.0, 2.0, 4.0], index=index)

    result = evaluate_factor(factor_values, forward)

    assert result["information_coefficient"] == pytest.approx(1.0)


def test_evaluate_factor_rejects_ambiguous_or_nonfinite_inputs():
    index = pd.date_range("2024-01-01", periods=3)
    with pytest.raises(ValueError, match="unique"):
        evaluate_factor(
            pd.Series([1.0, 2.0, 3.0], index=[index[0], index[0], index[1]]),
            pd.Series([1.0, 2.0, 3.0], index=[index[0], index[1], index[2]]),
        )
    with pytest.raises(ValueError, match="finite"):
        evaluate_factor(
            pd.Series([1.0, np.inf, 3.0], index=index),
            pd.Series([1.0, 2.0, 3.0], index=index),
        )
    with pytest.raises(ValueError, match="increasing"):
        evaluate_factor(
            pd.Series([1.0, 2.0, 3.0], index=index[::-1]),
            pd.Series([1.0, 2.0, 3.0], index=index[::-1]),
        )


def test_evaluate_factor_rejects_invalid_shift_periods():
    values = pd.Series([1.0, 2.0, 3.0])
    forward = pd.Series([1.0, 2.0, 3.0])
    for shift_periods in (-1, 1.5, True):
        with pytest.raises(ValueError, match="shift_periods"):
            evaluate_factor(values, forward, shift_periods=shift_periods)
