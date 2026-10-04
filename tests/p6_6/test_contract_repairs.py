from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance
from finahinking.p6_6 import (
    BacktestConfiguration,
    StrategyInterpreter,
    StrategyLab,
    builtin_feature_registry,
    compile_strategy,
    feature_graph_for_template,
    generate_educational_code,
    review_strategy,
    run_panel_backtest,
)
from finahinking.quant.multi_asset import MultiAssetDataset


def _panel() -> MultiAssetDataset:
    rows = []
    for date, prices in (
        ("2020-01-01", {"AAA": 100.0, "BBB": 100.0}),
        ("2020-01-02", {"AAA": 110.0, "BBB": 95.0}),
        ("2020-01-03", {"AAA": 121.0, "BBB": 90.0}),
        ("2020-01-04", {"AAA": 120.0, "BBB": 92.0}),
    ):
        for asset, close in prices.items():
            rows.append({"date": date, "asset": asset, "close": close, "available_at": date})
    return MultiAssetDataset(pd.DataFrame(rows), provider="fixture", source_url="offline://p6_6")


def test_low_volatility_threshold_keeps_values_at_or_below_threshold() -> None:
    frame = pd.DataFrame(
        {"close": [0.60, 0.6001]},
        index=pd.date_range("2024-01-01", periods=2),
    )
    values = builtin_feature_registry().evaluate("threshold_low_volatility", frame)
    assert values.tolist() == [1.0, 0.0]


def test_cross_sectional_rank_ranks_assets_within_each_date() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]),
            "asset": ["AAA", "BBB", "AAA", "BBB"],
            "close": [1.0, 2.0, 3.0, 1.0],
            "available_at": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]),
        },
    )
    graph, _ = feature_graph_for_template("lagged_momentum_low_volatility")
    # Evaluate the rank node directly with a one-node graph so its input is close.
    rank = graph.nodes[-1]
    values = builtin_feature_registry().evaluate(rank.feature, frame)
    assert values.tolist() == [0.5, 1.0, 1.0, 0.5]


def test_moving_average_compiler_honors_reviewed_window_parameter() -> None:
    accepted = StrategyInterpreter().accept(review_strategy("moving average trend")).spec
    spec = replace(accepted, parameters={**accepted.parameters, "moving_average_window": 3})
    ir, compiled = compile_strategy(spec)
    assert compiled is not None
    data = Dataset(
        pd.DataFrame({"close": [1.0, 2.0, 3.0, 2.0, 5.0]}, index=pd.date_range("2024-01-01", periods=5)),
        Provenance("fixture", "offline://p6_6"),
    )
    weights = compiled.generate(data)
    # At the final row, close=5 is above mean(2, 3, 2)=7/3 when the window is 3.
    assert weights.iloc[-1] == pytest.approx(0.75)
    assert ir.nodes[0].feature_id == "moving_average_3d"


def test_panel_backtest_uses_spec_parameters_and_backtest_costs() -> None:
    accepted = StrategyInterpreter().accept(review_strategy("momentum with low volatility")).spec
    spec = replace(
        accepted,
        parameters={**accepted.parameters, "lookback": 1, "selection_fraction": 1.0, "volatility_window": 2},
        cost_model={"fee_bps": 17.0, "slippage_bps": 3.0},
    )
    result = run_panel_backtest(spec, _panel())
    config = result["experiment"].backtest.config
    assert result["ir"].nodes[0].feature_id == "momentum_1d"
    assert result["ir"].nodes[1].feature_id == "volatility_2d"
    assert config.lookback == 1
    assert config.top_fraction == 1.0
    assert config.fee_bps == 17.0
    assert config.slippage_bps == 3.0

    configured = run_panel_backtest(
        spec,
        _panel(),
        BacktestConfiguration(starting_cash=12_345.0, fee_bps=2.0, slippage_bps=4.0),
    )
    configured_result = configured["experiment"].backtest
    assert configured_result.config.starting_cash == 12_345.0
    assert configured_result.config.fee_bps == 2.0
    assert configured_result.config.slippage_bps == 4.0


def test_panel_paper_flag_is_rejected_instead_of_silently_ignored() -> None:
    accepted = StrategyInterpreter().accept(review_strategy("momentum with low volatility"))
    with pytest.raises(ValueError, match="paper.*panel|panel.*paper"):
        StrategyLab().run(accepted, _panel(), paper=True)


def test_panel_educational_code_matches_date_rank_and_fractional_selection() -> None:
    accepted = StrategyInterpreter().accept(review_strategy("momentum with low volatility")).spec
    ir, _ = compile_strategy(accepted)
    generated = generate_educational_code(accepted, ir)
    assert "groupby(frame[\"date\"]).rank" in generated.source
    assert "selection_fraction" in generated.source
    assert "momentum > 0" not in generated.source
