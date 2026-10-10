from __future__ import annotations

import pytest

from finahinking.research.risk_runtime import RiskManager


def snapshot(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "snapshot_id": "snap-1",
        "as_of": "2026-10-01",
        "pit_status": "AVAILABLE",
        "drawdown": 0.05,
        "stress_results": {"base": {"passed": True}, "shock": {"passed": True}},
        "observations": (
            {"instrument": "AAA", "close": 100.0, "volume": 1000.0, "available_at": "2026-10-01"},
            {"instrument": "BBB", "close": 50.0, "volume": 1000.0, "available_at": "2026-10-01"},
        ),
    }
    value.update(overrides)
    return value


def good_factor() -> dict[str, object]:
    return {"status": "ADMITTED", "metrics": {"factor_score": 0.5}}


def limits(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "max_drawdown": 0.20,
        "max_concentration": 0.75,
        "min_liquidity": 100.0,
        "stress_scenarios": {"base": {"drawdown": 0.05}, "shock": {"drawdown": 0.10}},
    }
    value.update(overrides)
    return value


def test_risk_review_passes_only_with_pit_and_all_deterministic_gates() -> None:
    result = RiskManager().review(snapshot(), good_factor(), limits())
    assert result.passed is True
    assert result.status == "PASSED"
    assert result.blocking_reasons == ()
    assert result.paper_only is True


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"pit_status": "UNKNOWN"}, "PIT"),
        ({"pit_status": "UNAVAILABLE"}, "PIT"),
        ({"liquidity": 1.0}, "liquidity"),
        ({"concentration": 0.9}, "concentration"),
        ({"drawdown": 0.3}, "drawdown"),
        ({"stress_results": {"shock": {"passed": False}}}, "stress"),
    ],
)
def test_risk_review_fails_closed_for_unknown_or_failed_gates(change: dict[str, object], reason: str) -> None:
    value = snapshot(**change)
    result = RiskManager().review(value, good_factor(), limits())
    assert result.passed is False
    assert any(reason.casefold() in item.casefold() for item in result.blocking_reasons)


def test_risk_review_rejects_unsafe_live_inputs() -> None:
    with pytest.raises(ValueError, match="paper|broker|live|order"):
        RiskManager().review(snapshot(broker=lambda: None), good_factor(), limits())


def test_risk_review_blocks_missing_factor_status_drawdown_and_stress_results() -> None:
    missing_factor_status = RiskManager().review(snapshot(), {"metrics": {"drawdown": 0.05}}, limits())
    assert missing_factor_status.passed is False
    assert any("factor" in item.casefold() for item in missing_factor_status.blocking_reasons)

    missing_drawdown = snapshot()
    missing_drawdown.pop("drawdown")
    result = RiskManager().review(missing_drawdown, good_factor(), limits())
    assert result.passed is False
    assert any("drawdown" in item.casefold() for item in result.blocking_reasons)

    missing_stress = snapshot()
    missing_stress.pop("stress_results")
    result = RiskManager().review(missing_stress, good_factor(), limits())
    assert result.passed is False
    assert any("stress" in item.casefold() for item in result.blocking_reasons)
