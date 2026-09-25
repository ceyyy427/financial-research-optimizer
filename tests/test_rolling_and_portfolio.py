import numpy as np

from portfolio_robustness import factor_covariance, infeasible_fallback, ledoit_wolf_shrinkage, robust_covariance, sample_covariance
from rolling_split import build_windows
from config_utils import load_config


def test_expanding_windows_are_chronological(CONFIG):
    config = load_config(CONFIG)
    windows = build_windows(2000, config)
    assert windows
    assert windows[0]["train"] == (0, 756)
    assert windows[0]["validation"] == (756, 882)
    assert windows[0]["test"] == (882, 1134)
    assert all(window["train"][1] <= window["validation"][0] <= window["test"][0] for window in windows)


def test_covariance_estimators_and_fallback():
    rng = np.random.default_rng(7)
    returns = rng.normal(size=(80, 3))
    for covariance in (sample_covariance(returns), ledoit_wolf_shrinkage(returns), factor_covariance(returns), robust_covariance(returns)):
        assert covariance.shape == (3, 3)
        assert np.all(np.isfinite(covariance))
    fallback = infeasible_fallback("infeasible", [0.3, 0.4, 0.3])
    assert fallback["used"] is True
    assert fallback["action"] == "prior_weights"
