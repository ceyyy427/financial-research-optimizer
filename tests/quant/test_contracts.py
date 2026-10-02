import pandas as pd
import pytest

from finahinking.quant.interfaces import (
    BacktestConfig,
    BacktestResult,
    EvaluationReport,
    StrategyIntent,
    Trade,
)


def test_strategy_intent_and_trade_validate_temporal_financial_fields():
    timestamp = pd.Timestamp("2024-01-02", tz="UTC")
    intent = StrategyIntent(timestamp, target_weight=0.5, reason="fixture signal")
    trade = Trade(
        timestamp=timestamp,
        side="buy",
        quantity=2.0,
        price=101.0,
        notional=202.0,
        fees=0.202,
        slippage=0.101,
        reason="rebalance",
    )
    assert intent.target_weight == 0.5
    assert trade.notional == 202.0


def test_contracts_reject_invalid_weights_costs_and_trade_values():
    with pytest.raises(ValueError, match="target weight"):
        StrategyIntent(pd.Timestamp("2024-01-01"), target_weight=1.1, reason="bad")
    with pytest.raises(ValueError, match="fee"):
        BacktestConfig(starting_cash=100.0, fee_bps=-1.0, slippage_bps=0.0)
    with pytest.raises(ValueError, match="side"):
        Trade(pd.Timestamp("2024-01-01"), "hold", 1.0, 100.0, 100.0, 0.0, 0.0, "bad")


def test_backtest_result_and_evaluation_report_have_stable_fingerprints():
    config = BacktestConfig(starting_cash=1_000.0, fee_bps=5.0, slippage_bps=2.0)
    trade = Trade(pd.Timestamp("2024-01-02"), "buy", 2.0, 101.0, 202.0, 0.202, 0.101, "entry")
    result = BacktestResult(
        dataset_fingerprint="dataset-fingerprint",
        strategy_id="fixture",
        strategy_version="1",
        engine_version="p5.inhouse.0.1",
        config=config,
        equity_curve=(("2024-01-01T00:00:00+00:00", 1_000.0), ("2024-01-02T00:00:00+00:00", 998.0)),
        returns=(("2024-01-01T00:00:00+00:00", 0.0), ("2024-01-02T00:00:00+00:00", -0.002)),
        weights=(("2024-01-01T00:00:00+00:00", 0.0), ("2024-01-02T00:00:00+00:00", 0.5)),
        positions=(("2024-01-01T00:00:00+00:00", 0.0), ("2024-01-02T00:00:00+00:00", 2.0)),
        trades=(trade,),
        benchmark_returns=(("2024-01-01T00:00:00+00:00", 0.0), ("2024-01-02T00:00:00+00:00", 0.01)),
    )
    report = EvaluationReport(
        result_fingerprint=result.fingerprint,
        metrics={"total_return": -0.002, "sharpe": None},
        benchmark="buy_and_hold",
        limitations=("descriptive historical evidence only",),
    )
    assert result.fingerprint == BacktestResult.from_dict(result.to_dict()).fingerprint
    assert report.fingerprint == EvaluationReport.from_dict(report.to_dict()).fingerprint
