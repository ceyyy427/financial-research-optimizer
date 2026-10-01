import pandas as pd

from finahinking.factors.core import evaluate_factor, momentum_factor


def test_momentum_factor_contains_definition_and_limitations():
    factor = momentum_factor(window=2)
    assert factor.name == "momentum_2d"
    assert "look-ahead" in factor.limitations.lower()


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
