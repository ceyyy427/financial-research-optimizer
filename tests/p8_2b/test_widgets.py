from __future__ import annotations

import pytest

from finahinking.p8_2b.widgets import WidgetSpec, run_widget


def test_volatility_and_sharpe_widgets_are_deterministic_and_bounded() -> None:
    volatility = run_widget(WidgetSpec("v1", "volatility", {"returns": [0.01, -0.02, 0.03, 0.0], "annualization": 252}))
    assert volatility.values["observations"] == 4
    assert volatility.values["annualized_volatility"] == pytest.approx(0.3304542328)
    sharpe = run_widget(WidgetSpec("s1", "sharpe", {"returns": [0.01, 0.02, 0.0, 0.03], "risk_free": 0.0, "annualization": 252}))
    assert sharpe.values["sharpe"] == pytest.approx(18.4445113787)


def test_ols_momentum_and_oos_widgets_return_inspectable_results() -> None:
    ols = run_widget(WidgetSpec("o1", "ols", {"x": [1, 2, 3], "y": [2, 4, 6]}))
    assert ols.values["beta"] == pytest.approx(2.0)
    momentum = run_widget(WidgetSpec("m1", "momentum", {"prices": [100, 101, 103], "lookback": 2}))
    assert momentum.values["return"] == pytest.approx(0.03)
    oos = run_widget(WidgetSpec("o1", "oos_split", {"values": [1, 2, 3, 4], "train_ratio": 0.5}))
    assert oos.values["train"] == [1, 2]
    assert oos.values["oos"] == [3, 4]


def test_widgets_reject_nonfinite_and_unbounded_inputs() -> None:
    with pytest.raises(ValueError, match="finite"):
        run_widget(WidgetSpec("v1", "volatility", {"returns": [float("nan"), 0.1]}))
    with pytest.raises(ValueError, match="train_ratio"):
        run_widget(WidgetSpec("o1", "oos_split", {"values": [1, 2], "train_ratio": 0.1}))
