import numpy as np
import pandas as pd

from data_quality import audit_grain, quality_score, compare_schema
from execution_contract import validate_execution_contract
from forecast_contract import assess_ood, build_forecast_contract, combine_forecasts, target_check
from portfolio_diagnostics import benchmark_weights, fragility_report
from portfolio_robustness import compare_covariance_models, perturbation_ranges
from overfitting_applicability import assess_applicability


def test_data_quality_reports_grain_and_decision():
    frame = pd.DataFrame({
        "instrument_id": ["SPY", "SPY", "SPY"],
        "date": ["2026-01-01", "2026-01-02", "2026-01-02"],
        "field": ["close", "close", "close"],
        "unit": ["USD", "USD", "USD"],
    })
    grain = audit_grain(frame)
    assert grain["duplicate_grain_rows"] == 2
    report = {"rows": len(frame), "columns": list(frame), "missing_by_column": {}, "invalid_dates": 0,
              "duplicate_dates": 1, "date_end": "2026-01-02", "grain": grain}
    assert quality_score(report)["decision"] == "blocked"


def test_schema_drift_is_explicit():
    result = compare_schema({"close": {"type": "float", "unit": "USD"}}, {"close": {"type": "string", "unit": "CNY"}, "volume": {"type": "int"}})
    assert result["schema_drift_detected"] is True
    assert result["new_fields"] == ["volume"]
    assert result["changed_types"] == ["close"]


def test_execution_contract_blocks_same_close_execution():
    result = validate_execution_contract({"signal_time": "close", "decision_time": "close", "execution_time": "same_close", "execution_price": "close_plus_slippage", "market_calendar": "XNYS", "latency_bars": 0, "slippage_bps": 10, "partial_fill_rule": "pro_rata"})
    assert result["valid"] is False
    assert any("same-session" in error for error in result["errors"])


def test_forecast_contract_target_ensemble_and_ood():
    assert target_check("price", ["close"])["status"] == "warning"
    contract = build_forecast_contract("excess_return", ["point", "interval"])
    assert "coverage" in contract["metrics"]["interval"]
    result = combine_forecasts({"a": [1, 2], "b": [3, 4]}, {"a": 1, "b": 3}, method="inverse_error")
    assert result["weights"][0] > result["weights"][1]
    assert assess_ood({"x": [0, 0, 0]}, {"x": [1, 1]})["ood_status"] == "out_of_distribution"


def test_portfolio_benchmarks_covariance_and_fragility():
    rng = np.random.default_rng(5)
    returns = rng.normal(size=(100, 3))
    assert len(compare_covariance_models(returns)) == 4
    assert np.isclose(benchmark_weights(3).sum(), 1)
    fragile = fragility_report([0.9, 0.05, 0.05])
    assert fragile["status"] == "portfolio_fragile"
    ranges = perturbation_ranges([{"weights": [0.2, 0.8], "turnover": 0.1, "objective": 1}, {"weights": [0.4, 0.6], "turnover": 0.2, "objective": 2}])
    assert ranges["weight_intervals"]["asset_0"] == [0.2, 0.4]


def test_applicable_overfit_method_with_invalid_inputs_blocks():
    result = assess_applicability(3, 2, 50, paired_loss=True, portfolio_returns=True, diagnostic_inputs={"net_of_costs": False, "candidate_family": ["a", "b"], "pbo_splits": 4, "bootstrap_block_length": 5})
    methods = {row["method"]: row for row in result["methods"]}
    assert methods["DSR"]["status"] == "failed"
    assert result["gate_status"] == "failed"
