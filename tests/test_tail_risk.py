import numpy as np
import pytest

from portfolio_subset_test import effective_asset_subset_test
from factor_selection import fisher_screen
from tail_risk import bootstrap_tail_risk, compare_distribution_candidates, empirical_tail_risk, gaussian_tail_risk


def test_empirical_tail_risk_keeps_extreme_observations():
    losses = np.array([0.01, 0.02, 0.03, 0.04, 0.10, 0.20])
    result = empirical_tail_risk(losses, alpha=0.8)
    assert result["tail_count"] >= 1
    assert result["cvar"] >= result["var"]
    assert result["tail_conditional_variance"] >= 0


def test_moving_block_bootstrap_is_reproducible():
    losses = np.linspace(0.01, 0.20, 80)
    first = bootstrap_tail_risk(losses, replications=30, block_length=5, seed=11)
    second = bootstrap_tail_risk(losses, replications=30, block_length=5, seed=11)
    assert first["intervals"] == second["intervals"]
    assert first["method"] == "moving_block"


def test_distribution_registry_does_not_fake_unimplemented_fits():
    result = compare_distribution_candidates(np.random.default_rng(3).normal(size=100), candidates=["empirical", "gaussian", "student_t", "generalized_laplace", "elliptical_mixture"])
    statuses = {row["distribution"]: row["status"] for row in result["candidates"]}
    assert statuses["empirical"] == "ok"
    assert statuses["gaussian"] == "ok"
    assert statuses["student_t"] == "not_available"


def test_gaussian_tail_risk_rejects_zero_scale():
    with pytest.raises(ValueError, match="scale"):
        gaussian_tail_risk(np.ones(30))


def test_effective_asset_subset_test_returns_block_bootstrap_and_windows():
    rng = np.random.default_rng(8)
    base = rng.normal(size=(100, 2))
    candidate = (0.4 * base[:, :1] + rng.normal(size=(100, 1)) * 0.5)
    result = effective_asset_subset_test(base, candidate, replications=40, block_length=5, seed=9, rolling_windows=[(0, 40), (40, 80)])
    assert 0 <= result["p_value"] <= 1
    assert result["bootstrap"]["method"] == "moving_block"
    assert len(result["window_stability"]["windows"]) == 2


def test_effective_asset_subset_rejects_short_input():
    with pytest.raises(ValueError, match="20 rows"):
        effective_asset_subset_test(np.ones((10, 1)), np.ones((10, 1)))


def test_fisher_screen_is_train_window_explicit():
    features = np.array([[0.0, 1.0], [0.1, 1.1], [2.0, 1.0], [2.1, 1.1]])
    result = fisher_screen(features, [0, 0, 1, 1], ["macro", "noise"], max_features=1)
    assert result["selected_features"] == ["macro"]
    assert result["selection_scope"] == "training_window_only"
