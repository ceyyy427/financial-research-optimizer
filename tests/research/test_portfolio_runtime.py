from __future__ import annotations

import pytest

from finahinking.research.portfolio_runtime import PortfolioManager
from finahinking.research.risk_runtime import RiskManager


def snapshot() -> dict[str, object]:
    return {
        "snapshot_id": "snap-1",
        "as_of": "2026-10-01",
        "pit_status": "AVAILABLE",
        "observations": (
            {"instrument": "AAA", "close": 100.0, "volume": 1000.0, "available_at": "2026-10-01"},
            {"instrument": "BBB", "close": 50.0, "volume": 1000.0, "available_at": "2026-10-01"},
        ),
        "drawdown": 0.05,
        "stress_results": {"base": {"passed": True}, "shock": {"passed": True}},
    }


def risk() -> object:
    return RiskManager().review(
        snapshot(),
        {"status": "ADMITTED", "metrics": {"factor_score": 0.5}},
        {"max_drawdown": 0.20, "max_concentration": 0.75, "min_liquidity": 100.0, "stress_scenarios": {"shock": {"drawdown": 0.10}}},
    )


def test_portfolio_constructs_sorted_long_only_paper_weights() -> None:
    proposal = PortfolioManager().construct(risk(), ("BBB", "AAA"), {"max_single_weight": 0.6, "cash_buffer": 0.1})
    assert proposal.passed is True
    assert proposal.paper_only is True
    assert proposal.weights == {"AAA": 0.45, "BBB": 0.45}
    assert all(weight >= 0 for weight in proposal.weights.values())
    assert sum(proposal.weights.values()) <= 0.9


def test_portfolio_blocks_failed_risk_and_concentration() -> None:
    blocked = PortfolioManager().construct(
        RiskManager().review(snapshot(), {"status": "BLOCKED"}, {"max_drawdown": 0.2, "max_concentration": 0.8, "min_liquidity": 100.0, "stress_scenarios": {"shock": {"drawdown": 0.1}}}),
        ("AAA", "BBB"),
        {"max_single_weight": 0.6},
    )
    assert blocked.passed is False
    with pytest.raises(ValueError, match="long-only|weight|concentration"):
        PortfolioManager().construct(risk(), ("AAA",), {"long_only": False})


def test_portfolio_rejects_forged_risk_mapping_and_rechecks_risk_concentration() -> None:
    with pytest.raises(TypeError, match="RiskReviewResult"):
        PortfolioManager().construct({"passed": True}, ("AAA",), {"max_single_weight": 1.0})

    constrained = RiskManager().review(
        snapshot(),
        {"status": "ADMITTED", "metrics": {"factor_score": 0.5}},
        {"max_drawdown": 0.2, "max_concentration": 0.75, "min_liquidity": 100.0, "stress_scenarios": {"shock": {"drawdown": 0.1}}},
    )
    proposal = PortfolioManager().construct(constrained, ("AAA",), {"max_single_weight": 1.0})
    assert proposal.weights["AAA"] <= 0.75
