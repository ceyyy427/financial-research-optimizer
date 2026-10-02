import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance
from finahinking.quant.engines import BacktestEngine
from finahinking.quant.interfaces import BacktestConfig


class FixtureStrategy:
    strategy_id = "fixture-strategy"
    version = "v1"

    def __init__(self, weights):
        self.weights = weights

    def generate(self, dataset):
        return pd.Series(self.weights, index=dataset.frame.index, dtype=float)


def fixture_dataset():
    frame = pd.DataFrame(
        {"close": [100.0, 110.0, 105.0, 120.0]},
        index=pd.date_range("2024-01-01", periods=4, freq="D"),
    )
    return Dataset(frame, Provenance("fixture", "fixture://p5"))


def test_engine_shifts_target_weight_before_execution_to_prevent_lookahead():
    result = BacktestEngine().run(
        fixture_dataset(),
        FixtureStrategy([1.0, 0.0, 0.0, 0.0]),
        BacktestConfig(starting_cash=1_000.0, fee_bps=0.0, slippage_bps=0.0),
    )
    assert result.trades[0].timestamp == pd.Timestamp("2024-01-02")
    assert result.trades[0].side == "buy"
    assert result.weights[0][1] == 0.0


def test_engine_applies_explicit_fees_and_slippage_to_cash_and_equity():
    result = BacktestEngine().run(
        fixture_dataset(),
        FixtureStrategy([0.5, 0.5, 0.5, 0.0]),
        BacktestConfig(starting_cash=1_000.0, fee_bps=10.0, slippage_bps=20.0),
    )
    entry = result.trades[0]
    assert entry.fees > 0
    assert entry.slippage > 0
    assert result.equity_curve[-1][1] < 1_000.0 * 1.2
    assert result.fingerprint == BacktestEngine().run(
        fixture_dataset(),
        FixtureStrategy([0.5, 0.5, 0.5, 0.0]),
        BacktestConfig(starting_cash=1_000.0, fee_bps=10.0, slippage_bps=20.0),
    ).fingerprint


def test_engine_rejects_costs_that_create_negative_cash_when_disallowed():
    with pytest.raises(ValueError, match="negative cash"):
        BacktestEngine().run(
            Dataset(
                pd.DataFrame({"close": [100.0, 100.0]}, index=pd.date_range("2024-01-01", periods=2)),
                Provenance("fixture", "fixture://negative-cash"),
            ),
            FixtureStrategy([1.0, 0.0]),
            BacktestConfig(starting_cash=1.0, fee_bps=100.0, slippage_bps=0.0),
        )


def test_engine_rejects_strategy_index_drift():
    class DriftedStrategy(FixtureStrategy):
        def generate(self, dataset):
            return pd.Series([0.0] * len(dataset.frame), index=dataset.frame.index + pd.Timedelta(days=1))

    with pytest.raises(ValueError, match="index"):
        BacktestEngine().run(
            fixture_dataset(),
            DriftedStrategy([0.0, 0.0, 0.0, 0.0]),
            BacktestConfig(starting_cash=1_000.0, fee_bps=0.0, slippage_bps=0.0),
        )
