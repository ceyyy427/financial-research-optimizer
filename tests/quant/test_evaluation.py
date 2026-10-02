import pandas as pd
import pytest

from finahinking.quant.evaluation.metrics import evaluate_backtest
from finahinking.quant.interfaces import BacktestConfig, BacktestResult, Trade


def result_fixture():
    config = BacktestConfig(starting_cash=100.0, fee_bps=5.0, slippage_bps=2.0, annualization=4)
    trades = (
        Trade(pd.Timestamp("2024-01-02"), "buy", 0.5, 100.0, 50.0, 0.025, 0.01, "entry"),
        Trade(pd.Timestamp("2024-01-04"), "sell", 0.5, 103.0, 51.5, 0.02575, 0.0103, "exit"),
    )
    return BacktestResult(
        dataset_fingerprint="dataset",
        strategy_id="fixture",
        strategy_version="v1",
        engine_version="p5.inhouse.0.1",
        config=config,
        equity_curve=(
            ("2024-01-01T00:00:00", 100.0),
            ("2024-01-02T00:00:00", 102.0),
            ("2024-01-03T00:00:00", 101.0),
            ("2024-01-04T00:00:00", 103.0),
        ),
        returns=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", 0.02), ("2024-01-03T00:00:00", -1 / 102), ("2024-01-04T00:00:00", 2 / 101)),
        weights=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", 0.5), ("2024-01-03T00:00:00", 0.5), ("2024-01-04T00:00:00", 0.0)),
        positions=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", 0.5), ("2024-01-03T00:00:00", 0.5), ("2024-01-04T00:00:00", 0.0)),
        trades=trades,
        benchmark_returns=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", 0.01), ("2024-01-03T00:00:00", 0.0), ("2024-01-04T00:00:00", 0.01)),
    )


def test_evaluation_reports_returns_risk_costs_turnover_and_benchmark():
    report = evaluate_backtest(result_fixture())
    assert report.metrics["total_return"] == pytest.approx(0.03)
    assert report.metrics["max_drawdown"] == pytest.approx(101 / 102 - 1)
    assert report.metrics["benchmark_return"] == pytest.approx(0.0201)
    assert report.metrics["turnover"] == pytest.approx((50.0 + 51.5) / 100.0)
    assert report.metrics["total_fees"] == pytest.approx(0.05075)
    assert report.metrics["total_slippage"] == pytest.approx(0.0203)
    assert report.metrics["sharpe"] is not None
    assert "descriptive" in report.limitations[0]


def test_evaluation_returns_none_for_zero_volatility_and_short_series():
    result = result_fixture()
    constant = BacktestResult(
        dataset_fingerprint=result.dataset_fingerprint,
        strategy_id=result.strategy_id,
        strategy_version=result.strategy_version,
        engine_version=result.engine_version,
        config=result.config,
        equity_curve=(("2024-01-01T00:00:00", 100.0), ("2024-01-02T00:00:00", 100.0)),
        returns=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", 0.0)),
        weights=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", 0.0)),
        positions=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", 0.0)),
        trades=(),
        benchmark_returns=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", 0.0)),
    )
    report = evaluate_backtest(constant)
    assert report.metrics["volatility"] == 0.0
    assert report.metrics["sharpe"] is None
    assert report.metrics["sortino"] is None


def test_sortino_uses_one_annualization_factor():
    result = result_fixture()
    result = BacktestResult(
        dataset_fingerprint=result.dataset_fingerprint,
        strategy_id=result.strategy_id,
        strategy_version=result.strategy_version,
        engine_version=result.engine_version,
        config=result.config,
        equity_curve=(("2024-01-01T00:00:00", 100.0), ("2024-01-02T00:00:00", 90.0), ("2024-01-03T00:00:00", 72.0), ("2024-01-04T00:00:00", 79.2)),
        returns=(("2024-01-01T00:00:00", 0.0), ("2024-01-02T00:00:00", -0.1), ("2024-01-03T00:00:00", -0.2), ("2024-01-04T00:00:00", 0.1)),
        weights=result.weights,
        positions=result.positions,
        trades=result.trades,
        benchmark_returns=result.benchmark_returns,
    )
    report = evaluate_backtest(result)
    daily_downside = ((0.1**2 + 0.2**2) / 2) ** 0.5
    expected = (-0.05 * 4**0.5) / (daily_downside * 4**0.5)
    assert report.metrics["sortino"] == pytest.approx(expected)


def test_evaluation_report_defensively_copies_metrics():
    report = evaluate_backtest(result_fixture())
    exposed = report.metrics
    exposed["total_return"] = 99.0
    assert report.metrics["total_return"] != 99.0
