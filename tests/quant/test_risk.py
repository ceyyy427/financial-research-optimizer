import pandas as pd
import pytest

from finahinking.quant.risk.metrics import (
    conditional_value_at_risk,
    downside_deviation,
    maximum_drawdown,
    value_at_risk,
)


def test_risk_metrics_measure_drawdown_and_lower_tail_losses():
    equity = pd.Series([100.0, 110.0, 99.0, 108.0])
    returns = pd.Series([0.10, 0.05, -0.10, -0.20])
    assert maximum_drawdown(equity) == pytest.approx(99 / 110 - 1)
    assert downside_deviation(returns, annualization=4) > 0
    assert value_at_risk(returns, confidence=0.5) == pytest.approx(0.025)
    assert conditional_value_at_risk(returns, confidence=0.5) == pytest.approx(0.15)


def test_risk_metrics_return_none_for_undefined_inputs():
    assert maximum_drawdown(pd.Series([100.0])) == 0.0
    assert downside_deviation(pd.Series([0.01]), annualization=252) is None
    assert value_at_risk(pd.Series([0.01]), confidence=0.95) is None
    assert conditional_value_at_risk(pd.Series([0.01]), confidence=0.95) is None
