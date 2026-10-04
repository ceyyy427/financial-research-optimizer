from __future__ import annotations

import pytest

from finahinking.p6_6.workbench import (
    ExecutionPolicy,
    FaultPolicy,
    PositionPolicySpec,
    RiskStatePolicy,
)
from finahinking.p6_6.workbench_engine import run_workbench


def observations() -> list[dict[str, object]]:
    return [
        {"id": "a-1", "time": "2026-01-01", "instrument": "AAA", "score": 0.9, "signal": True, "volatility": 0.10, "return": 0.01, "price": 100, "volume": 1000},
        {"id": "b-1", "time": "2026-01-01", "instrument": "BBB", "score": 0.3, "signal": True, "volatility": 0.20, "return": 0.00, "price": 50, "volume": 1000},
        {"id": "a-2", "time": "2026-01-02", "instrument": "AAA", "score": 0.8, "signal": True, "volatility": 0.10, "return": -0.02, "price": 98, "volume": 1000},
        {"id": "b-2", "time": "2026-01-02", "instrument": "BBB", "score": 0.1, "signal": False, "volatility": 0.20, "return": 0.01, "price": 50.5, "volume": 1000},
    ]


def policies() -> tuple[PositionPolicySpec, RiskStatePolicy, ExecutionPolicy, FaultPolicy]:
    return (
        PositionPolicySpec(policy_id="equal", version="v1", mapping="equal_weight", target_volatility=0.20, max_single_weight=0.75, max_exposure=0.90, cash_buffer=0.10),
        RiskStatePolicy(policy_id="risk", version="v1", thresholds={"caution_volatility": 0.18, "defensive_volatility": 0.30, "freeze_drawdown": 0.20, "recovery_drawdown": 0.05}),
        ExecutionPolicy(policy_id="exec", version="v1", fee_bps=5, slippage_bps=5, stress_slippage_bps=15),
        FaultPolicy(policy_id="faults", version="v1"),
    )


def test_engine_separates_signal_weight_risk_and_execution() -> None:
    run = run_workbench("run-engine", observations(), *policies())
    first = [point for point in run.points if point.time == "2026-01-01"]
    assert sum(point.raw_weight for point in first) == pytest.approx(0.9)
    assert all(0 <= point.final_weight <= 0.75 for point in first)
    assert all(point.risk_scale <= 1 for point in first)
    assert all(point.cash == pytest.approx(0.1) for point in first)
    assert all(point.held_weight == 0 for point in first)
    assert any(point.trade_weight for point in run.points)


def test_inverse_volatility_and_rank_weight_are_deterministic() -> None:
    for mapping in ("rank_weight", "inverse_volatility", "risk_budget"):
        position, risk, execution, faults = policies()
        position = PositionPolicySpec(**{**position.to_dict(), "mapping": mapping})
        first = run_workbench("run-engine", observations(), position, risk, execution, faults)
        second = run_workbench("run-engine", observations(), position, risk, execution, faults)
        assert first.fingerprint == second.fingerprint
        weights = {point.instrument: point.raw_weight for point in first.points if point.time == "2026-01-01"}
        assert weights["AAA"] > weights["BBB"]


def test_risk_state_and_stale_data_create_auditable_faults() -> None:
    position, risk, execution, faults = policies()
    risky = observations()
    risky[2] = {**risky[2], "volatility": 0.40, "drawdown": 0.25}
    risky[3] = {**risky[3], "stale": True}
    run = run_workbench("run-risk", risky, position, risk, execution, faults)
    second = [point for point in run.points if point.time == "2026-01-02"]
    assert {point.risk_state for point in second} & {"DEFENSIVE", "FREEZE", "FLATTEN"}
    assert any(event["kind"] == "DATA_STALE" for point in second for event in point.fault_events)
    # FREEZE preserves current holdings; only pre-authorized FLATTEN exits them.
    assert all(point.trade_weight == 0 for point in second if point.risk_state == "FREEZE")


def test_invalid_observation_is_rejected_before_calculation() -> None:
    with pytest.raises(ValueError, match="score"):
        run_workbench("run-bad", [{"id": "bad", "time": "2026-01-01", "instrument": "AAA", "score": float("nan")}], *policies())


def test_costs_and_returns_use_next_period_holdings_not_current_scores() -> None:
    rows = [
        {"id": "p1", "time": "2026-01-01", "instrument": "AAA", "score": 1, "signal": True, "return": 0.5},
        {"id": "p2", "time": "2026-01-02", "instrument": "AAA", "score": 0, "signal": False, "return": 0.1},
        {"id": "p3", "time": "2026-01-03", "instrument": "AAA", "score": 0, "signal": False, "return": -0.5},
    ]
    run = run_workbench("timing", rows, PositionPolicySpec("equal", "v1", "equal_weight"), RiskStatePolicy("risk", "v1"), ExecutionPolicy("execution", "v1", fee_bps=10, slippage_bps=0), FaultPolicy("faults", "v1"))
    assert run.points[0].net_return == 0
    assert run.points[1].net_return == pytest.approx(0.099)
    assert run.points[2].net_return == pytest.approx(-0.001)
    assert run.metrics["total_return"] == pytest.approx(1.099 * 0.999 - 1)


def test_projection_respects_turnover_cash_and_liquidity() -> None:
    p = PositionPolicySpec("limited", "v1", "equal_weight", max_turnover=0.2, max_trade_weight=0.15, liquidity_participation=0.01)
    rows = [{"id": f"p{i}", "time": f"2026-01-0{i}", "instrument": "AAA", "score": 1, "signal": True, "liquidity_weight": 5} for i in (1, 2, 3)]
    run = run_workbench("limited", rows, p, RiskStatePolicy("risk", "v1"), ExecutionPolicy("execution", "v1", liquidity_participation=0.01), FaultPolicy("fault", "v1"))
    assert max(abs(point.trade_weight) for point in run.points) <= 0.05 + 1e-12
    assert all(point.exposure <= 1 and point.cash >= 0 for point in run.points)


def test_stale_data_preserves_holdings_and_records_skip() -> None:
    rows = [
        {"id": "p1", "time": "2026-01-01", "instrument": "AAA", "score": 1, "signal": True},
        {"id": "p2", "time": "2026-01-02", "instrument": "AAA", "score": 1, "signal": True, "stale": True},
    ]
    run = run_workbench("stale", rows, *policies())
    assert run.points[1].trade_weight == 0
    assert run.points[1].fault_events[0]["action"] == "SKIP"


def test_minimum_duration_and_hysteresis_stop_state_chattering() -> None:
    from finahinking.p6_6.workbench_engine import transition_risk
    policy = RiskStatePolicy("risk", "v1", minimum_duration=2, hysteresis=0.02)
    state, age, _ = transition_risk("CAUTION", 1, {"volatility": 0.05, "drawdown": 0}, policy)
    assert (state, age) == ("CAUTION", 2)
    state, age, _ = transition_risk(state, age, {"volatility": 0.17, "drawdown": 0}, policy)
    assert state == "CAUTION"
    state, age, _ = transition_risk(state, age, {"volatility": 0.05, "drawdown": 0}, policy)
    assert state == "RECOVERY"
