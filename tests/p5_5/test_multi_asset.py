import pandas as pd

from finahinking.quant.multi_asset import (
    CrossSectionalMomentumConfig,
    MultiAssetDataset,
    run_cross_sectional_momentum_experiment,
)


def _panel() -> MultiAssetDataset:
    rows = []
    for date, a, b in [
        ("2020-01-01", 100, 100),
        ("2020-01-02", 110, 95),
        ("2020-01-03", 121, 90),
        ("2020-01-04", 120, 92),
        ("2020-01-05", 130, 88),
    ]:
        for asset, close in (("AAA", a), ("BBB", b)):
            rows.append({"date": date, "asset": asset, "close": close, "available_at": date})
    return MultiAssetDataset(pd.DataFrame(rows), provider="fixture", source_url="offline://p5_5")


def test_cross_sectional_slice_is_lagged_costed_and_reproducible() -> None:
    config = CrossSectionalMomentumConfig(lookback=2, top_fraction=0.5, fee_bps=10, slippage_bps=5)
    first = run_cross_sectional_momentum_experiment(
        _panel(), config, question="Does momentum separate?", hypothesis="AAA leads after lag"
    )
    second = run_cross_sectional_momentum_experiment(
        _panel(), config, question="Does momentum separate?", hypothesis="AAA leads after lag"
    )
    assert first.quant_run.fingerprint == second.quant_run.fingerprint
    assert first.research_run.result["quant_run_id"] == first.quant_run.quant_run_id
    assert first.artifact.fingerprint == first.quant_run.result_artifact.fingerprint
    assert "LIQUIDITY_NOT_MODELED" in first.warnings
    assert first.evaluation.metrics["turnover"] >= 0
    assert first.evaluation.metrics["trade_count"] > 0

    no_cost = run_cross_sectional_momentum_experiment(
        _panel(),
        CrossSectionalMomentumConfig(lookback=2, top_fraction=0.5, fee_bps=0, slippage_bps=0),
        question="Does momentum separate?",
        hypothesis="AAA leads after lag",
    )
    assert first.evaluation.metrics["total_return"] <= no_cost.evaluation.metrics["total_return"]
