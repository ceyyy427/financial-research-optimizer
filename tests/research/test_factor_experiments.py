from __future__ import annotations

import pandas as pd
import pytest

from finahinking.research.factor_experiments import FactorExperimentSpec, run_factor_experiments
from finahinking.research.reports import compare_experiments


def _dataset() -> dict[str, object]:
    index = pd.date_range("2024-01-01", periods=48, freq="D", tz="UTC")
    close = pd.Series([100 + i + i % 3 for i in range(len(index))], index=index, dtype=float)
    return {"frame": pd.DataFrame({"close": close}, index=index), "forward_return": close.pct_change().shift(-1)}


def test_grid_budget_pit_oos_fingerprint_and_decay_ranking() -> None:
    spec = FactorExperimentSpec({"expression": ["rank(close)", "negate(rank(close))"], "window": [5, 10]}, max_experiments=3, decay_horizons=(1, 3))
    result = run_factor_experiments(spec, _dataset(), {"min_samples": 4})
    assert len(result.experiments) == 3
    assert result.ranking
    assert result.experiments[0].evaluation.oos_status == "HIDDEN"
    assert set(result.experiments[0].decay) == {"1", "3"}
    assert all(item.dataset_fingerprint == result.dataset_fingerprint for item in result.experiments)
    assert all(item.config_digest == result.config_digest and item.research_fingerprint == result.research_fingerprint for item in result.experiments)
    assert compare_experiments(result.to_dict())["paper_only"] is True


def test_repeated_run_is_byte_deterministic() -> None:
    spec = FactorExperimentSpec({"expression": ["rank(close)", "negate(rank(close))"]}, max_experiments=2)
    first = run_factor_experiments(spec, _dataset(), {"min_samples": 4})
    second = run_factor_experiments(spec, _dataset(), {"min_samples": 4})
    assert first.experiment_digest == second.experiment_digest
    assert first.to_dict() == second.to_dict()


def test_unordered_axes_are_stably_normalized_before_budget_truncation() -> None:
    spec = FactorExperimentSpec({"expression": {"rank(close)", "negate(rank(close))"}}, max_experiments=2)
    first = run_factor_experiments(spec, _dataset(), {"min_samples": 4})
    second = run_factor_experiments(spec, _dataset(), {"min_samples": 4})
    assert [item.parameters for item in first.experiments] == [item.parameters for item in second.experiments]
    assert first.experiment_digest == second.experiment_digest


@pytest.mark.parametrize("budget", [0, -1, 257, True])
def test_invalid_budgets_and_grids_fail_clearly(budget) -> None:
    with pytest.raises(ValueError, match="max_experiments"):
        FactorExperimentSpec({"window": [5]}, max_experiments=budget)
    with pytest.raises(ValueError, match="parameter axis"):
        FactorExperimentSpec({"window": []})


def test_non_string_keys_and_nonfinite_splits_are_rejected() -> None:
    with pytest.raises(TypeError, match="keys"):
        FactorExperimentSpec({1: [5]})
    with pytest.raises(ValueError, match="finite"):
        FactorExperimentSpec({"window": [5]}, split={"train": float("nan"), "validation": 0.2, "test": 0.2})
    with pytest.raises(ValueError, match="finite"):
        FactorExperimentSpec({"window": [5]}, split={"train": float("inf"), "validation": 0.2, "test": 0.2})
