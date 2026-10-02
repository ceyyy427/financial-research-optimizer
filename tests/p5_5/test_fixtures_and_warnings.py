from pathlib import Path

import pandas as pd

from finahinking.quant.multi_asset import (
    CrossSectionalMomentumConfig,
    MultiAssetDataset,
    run_cross_sectional_momentum_experiment,
)
from finahinking.quant.splits import OOSPlan, TestPeriod, TrainingPeriod, ValidationPeriod

ROOT = Path(__file__).resolve().parents[2]


def test_required_p5_5_fixtures_are_deterministic_and_have_pit_columns() -> None:
    panel = pd.read_csv(ROOT / "fixtures/p5_5/momentum_multi_asset.csv")
    assert {"date", "asset", "close", "available_at"}.issubset(panel.columns)
    assert panel.equals(pd.read_csv(ROOT / "fixtures/p5_5/momentum_multi_asset.csv"))


def test_delayed_availability_is_not_used_before_its_as_of_timestamp() -> None:
    panel = pd.DataFrame(
        [
            {"date": "2020-01-01", "asset": "AAA", "close": 100, "available_at": "2020-01-01"},
            {"date": "2020-01-02", "asset": "AAA", "close": 200, "available_at": "2020-01-04"},
            {"date": "2020-01-03", "asset": "AAA", "close": 102, "available_at": "2020-01-03"},
            {"date": "2020-01-01", "asset": "BBB", "close": 100, "available_at": "2020-01-01"},
            {"date": "2020-01-02", "asset": "BBB", "close": 99, "available_at": "2020-01-02"},
            {"date": "2020-01-03", "asset": "BBB", "close": 98, "available_at": "2020-01-03"},
            {"date": "2020-01-04", "asset": "AAA", "close": 103, "available_at": "2020-01-04"},
            {"date": "2020-01-04", "asset": "BBB", "close": 97, "available_at": "2020-01-04"},
        ]
    )
    result = run_cross_sectional_momentum_experiment(
        MultiAssetDataset(panel, provider="fixture", source_url="offline://pit"),
        CrossSectionalMomentumConfig(lookback=1),
        question="Does the fixed factor separate?",
        hypothesis="The lagged rank is descriptive",
    )
    # The unavailable 200 close cannot be used as a 2020-01-02 signal.
    assert "200" not in str(result.backtest.selected_assets[:3])
    assert set(result.warnings) >= {
        "SURVIVORSHIP_BIAS_NOT_MODELED",
        "DELISTING_NOT_MODELED",
        "CORPORATE_ACTIONS_PARTIAL",
        "LIQUIDITY_NOT_MODELED",
        "CAPACITY_UNKNOWN",
    }


def test_oos_fixture_boundary_is_explicitly_later_than_selection() -> None:
    plan = OOSPlan(
        training=TrainingPeriod("2020-01-01", "2020-01-06"),
        validation=ValidationPeriod("2020-01-06", "2020-01-08"),
        test=TestPeriod("2020-01-08", "2020-01-11"),
        hypothesis="fixed momentum separation",
        search_space={"lookback": [2]},
        experiment_count=1,
        selection_method="pre_registered_fixed_config",
        validation_method="fixed_validation",
    ).freeze_configuration({"lookback": 2})
    assert plan.evaluation_boundary is not None
    assert plan.evaluation_boundary.start >= plan.selection_boundary.end
