from __future__ import annotations

from finahinking.p6_6.workbench import (
    ExecutionPolicy,
    FaultPolicy,
    PositionPolicySpec,
    RiskStatePolicy,
)
from finahinking.p6_6.workbench_engine import run_workbench
from finahinking.p6_6.workbench_explanations import build_explanation_package


def run():
    return run_workbench(
        "explain-run",
        [
            {"id": "a1", "time": "2026-01-01", "instrument": "AAA", "score": 0.7, "signal": True, "volatility": 0.1, "return": 0},
            {"id": "a2", "time": "2026-01-02", "instrument": "AAA", "score": 0.9, "signal": True, "volatility": 0.1, "return": 0.02},
        ],
        PositionPolicySpec("position", "v1", "equal_weight"),
        RiskStatePolicy("risk", "v1"),
        ExecutionPolicy("execution", "v1"),
        FaultPolicy("fault", "v1"),
    )


def test_explanation_package_contains_nine_teaching_blocks_and_trace_refs() -> None:
    package = build_explanation_package(
        run(),
        strategy_id="strategy-1",
        parameter_changes={"lookback": {"before": 20, "after": 40}},
        intent="Reduce noise without hiding costs.",
        formula_before="P(t-1)/P(t-21)-1",
        formula_after="P(t-1)/P(t-41)-1",
        code_trace=("momentum", "lag"),
        next_experiment="Replay with the same cost policy.",
    )
    trace = package["traces"]["momentum"]
    assert set(trace) == {"concept", "intuition", "math", "derivation", "code", "finance", "parameter", "result", "assumptions"}
    assert package["parameter_change"]["attribution"]["status"] == "ATTRIBUTION_AVAILABLE"
    assert package["evidence"]["run_fingerprint"] == run().fingerprint
    assert package["paper_only"] is True


def test_multi_parameter_explanation_refuses_single_parameter_causality() -> None:
    package = build_explanation_package(
        run(),
        strategy_id="strategy-1",
        parameter_changes={"lookback": {"before": 20, "after": 40}, "fee_bps": {"before": 5, "after": 8}},
        intent="Change signal horizon and friction together.",
        formula_before="m20",
        formula_after="m40",
        code_trace=("momentum", "costs"),
        next_experiment="Hold fees constant and replay only lookback.",
    )
    assert package["parameter_change"]["attribution"]["status"] == "ATTRIBUTION_CONFOUNDED"
    assert any("single" in item.lower() for item in package["parameter_change"]["limitations"])


def test_explanation_uses_paired_metrics_and_carries_limitations() -> None:
    baseline = run().metrics
    variant = {**baseline, "total_return": baseline["total_return"] + 0.01}
    package = build_explanation_package(
        run(),
        strategy_id="strategy-1",
        parameter_changes={"max_single_weight": {"before": 1.0, "after": 0.5}},
        intent="Reduce concentration.",
        formula_before="w_i",
        formula_after="min(w_i, 0.5)",
        baseline_metrics=baseline,
        variant_metrics=variant,
        code_trace=("weights",),
        next_experiment="Check the same cap under stress slippage.",
    )
    assert package["parameter_change"]["paired_metrics"]["variant"]["total_return"] == variant["total_return"]
    assert package["parameter_change"]["attribution"]["delta"]["total_return"] == 0.01
    assert package["limitations"]
