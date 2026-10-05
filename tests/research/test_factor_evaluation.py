from __future__ import annotations

import pandas as pd
import pytest

from finahinking.factors.evaluation import (
    FactorEvaluationStatus,
    build_factor_admission,
    evaluate_factor_candidate,
)
from finahinking.factors.mining import FactorCandidate


def _candidate() -> FactorCandidate:
    return FactorCandidate(
        candidate_id="candidate-1",
        expression="rank(close)",
        hypothesis="price strength",
        source="fixture",
        metadata={"direction": "positive"},
    )


def _data() -> tuple[pd.DataFrame, pd.Series]:
    index = pd.date_range("2024-01-01", periods=24, freq="D", tz="UTC")
    close = pd.Series([100 + i + (i % 3) for i in range(len(index))], index=index, dtype=float)
    frame = pd.DataFrame({"close": close}, index=index)
    forward = close.pct_change().shift(-1).rename("forward_return")
    return frame, forward


def test_evaluation_aligns_t_plus_one_and_reports_metrics_and_decay() -> None:
    frame, forward = _data()
    result = evaluate_factor_candidate(
        _candidate(),
        frame,
        forward,
        {"shift_periods": 1, "min_samples": 8, "oos": True, "decay_horizons": (1, 3)},
    )

    assert result.status is FactorEvaluationStatus.VALID
    assert result.sample_size >= 8
    assert result.information_coefficient is not None
    assert result.information_ratio is not None
    assert len(result.decay.horizons) == 2
    assert result.evidence_refs
    assert result.fingerprint


def test_evaluation_blocks_leakage_and_insufficient_samples() -> None:
    frame, forward = _data()
    leakage = evaluate_factor_candidate(_candidate(), frame, forward, {"shift_periods": 0, "oos": True})
    small = evaluate_factor_candidate(_candidate(), frame.iloc[:3], forward.iloc[:3], {"shift_periods": 1, "min_samples": 8, "oos": True})

    assert leakage.status is FactorEvaluationStatus.LEAKAGE_BLOCKED
    assert small.status is FactorEvaluationStatus.INSUFFICIENT_DATA


def test_evaluation_rejects_future_availability_and_admission_has_reasons() -> None:
    frame, forward = _data()
    with pytest.raises(ValueError, match="availability"):
        evaluate_factor_candidate(
            _candidate(),
            frame,
            forward,
            {"shift_periods": 1, "as_of": frame.index[10], "available_at": {"close": frame.index[11]}},
        )
    result = evaluate_factor_candidate(_candidate(), frame, forward, {"shift_periods": 1, "min_samples": 8, "oos": True})
    decision = build_factor_admission(result, {"min_abs_ic": 2.0, "min_icir": 2.0})
    assert decision.status == "REJECTED"
    assert decision.reasons

