"""Bounded factor-research coordinator built on Finathink-native contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

import pandas as pd

from finahinking.factors.evaluation import (
    FactorAdmissionDecision,
    FactorEvaluation,
    build_factor_admission,
    evaluate_factor_candidate,
)
from finahinking.factors.mining import FactorCandidate
from finahinking.p6_6.workbench import ResearchCharter, _digest


class FactorResearchState(str, Enum):
    CHARTER_FROZEN = "CHARTER_FROZEN"
    CANDIDATE_GENERATED = "CANDIDATE_GENERATED"
    TRAIN_EVALUATED = "TRAIN_EVALUATED"
    VALIDATION_EVALUATED = "VALIDATION_EVALUATED"
    CANDIDATE_POOL = "CANDIDATE_POOL"
    REJECTED = "REJECTED"
    STRATEGY_FROZEN = "STRATEGY_FROZEN"
    TEST_EVALUATED = "TEST_EVALUATED"
    RESEARCH_REVIEW = "RESEARCH_REVIEW"


@dataclass(frozen=True, slots=True)
class FactorResearchRound:
    round_index: int
    candidate: FactorCandidate
    evaluation: FactorEvaluation
    admission: FactorAdmissionDecision
    train_evaluation: FactorEvaluation | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "candidate": self.candidate.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "admission": self.admission.to_dict(),
            "train_evaluation": None if self.train_evaluation is None else self.train_evaluation.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class FactorResearchRun:
    charter: ResearchCharter
    state: FactorResearchState
    rounds: tuple[FactorResearchRound, ...]
    selected_candidate: str | None = None
    test_evaluation: FactorEvaluation | None = None

    @property
    def fingerprint(self) -> str:
        return self.to_dict()["fingerprint"]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "charter": self.charter.to_dict(),
            "state": self.state.value,
            "rounds": [item.to_dict() for item in self.rounds],
            "selected_candidate": self.selected_candidate,
            "test_evaluation": None if self.test_evaluation is None else self.test_evaluation.to_dict(),
        }
        payload["fingerprint"] = _digest(payload)
        return payload

    def freeze(self, candidate_id: str) -> FactorResearchRun:
        if self.state is not FactorResearchState.CANDIDATE_POOL:
            raise ValueError("only the candidate pool can be frozen")
        selected = next((item for item in self.rounds if item.candidate.candidate_id == candidate_id and item.admission.status == "ADMITTED"), None)
        if selected is None:
            raise ValueError("only an admitted candidate can be frozen")
        return replace(self, state=FactorResearchState.STRATEGY_FROZEN, selected_candidate=candidate_id, charter=self.charter.freeze_test())

    def evaluate_test(self, dataset: Mapping[str, Any]) -> FactorResearchRun:
        if self.test_evaluation is not None:
            raise ValueError("test evaluation is once-only")
        if self.state is not FactorResearchState.STRATEGY_FROZEN or self.selected_candidate is None:
            raise ValueError("test evaluation requires a frozen strategy")
        candidate = next(item.candidate for item in self.rounds if item.candidate.candidate_id == self.selected_candidate)
        result = evaluate_factor_candidate(
            candidate,
            _frame(dataset),
            _forward(dataset),
            _phase_spec(self.charter, _frame(dataset), "test"),
        )
        return replace(self, state=FactorResearchState.TEST_EVALUATED, test_evaluation=result)


def _frame(dataset: Mapping[str, Any]) -> pd.DataFrame:
    frame = dataset.get("frame")
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("dataset.frame must be a DataFrame")
    return frame


def _forward(dataset: Mapping[str, Any]) -> pd.Series:
    forward = dataset.get("forward_return")
    if not isinstance(forward, pd.Series):
        raise TypeError("dataset.forward_return must be a Series")
    return forward


def _phase_spec(charter: ResearchCharter, frame: pd.DataFrame, phase: str) -> dict[str, Any]:
    if frame.empty:
        raise ValueError("factor research requires a non-empty dataset")
    train_ratio = float(charter.data_split.get("train", 0.6))
    validation_ratio = float(charter.data_split.get("validation", 0.2))
    test_ratio = float(charter.data_split.get("test", 0.2))
    if not all(0 < value < 1 for value in (train_ratio, validation_ratio, test_ratio)) or abs(train_ratio + validation_ratio + test_ratio - 1) > 1e-9:
        raise ValueError("charter data_split must contain positive train/validation/test ratios summing to one")
    train_end = int(len(frame) * train_ratio)
    validation_end = int(len(frame) * (train_ratio + validation_ratio))
    starts = {"train": 0, "validation": train_end, "test": validation_end}
    ends = {"train": train_end, "validation": validation_end, "test": len(frame)}
    start, end = starts[phase], ends[phase]
    # A forward label at the final feature row crosses the phase boundary, so
    # the last row is purged. This keeps the first OOS row out of validation.
    score_end = max(start, end - 2)
    cutoff = frame.index[score_end]
    phase_samples = max(0, score_end - start + 1)
    return {
        **dict(charter.hard_constraints),
        "phase": phase,
        "oos": phase == "test",
        "train_ratio": train_ratio,
        "validation_ratio": validation_ratio,
        "evaluation_start": frame.index[min(start, len(frame) - 1)],
        "evaluation_end": cutoff,
        "as_of": cutoff,
        "min_samples": int(dict(charter.hard_constraints).get("min_samples", min(8, max(2, phase_samples)))),
    }


def run_factor_research(
    charter: ResearchCharter,
    candidates: Sequence[FactorCandidate],
    dataset: Mapping[str, Any],
    limits: Mapping[str, Any] | None = None,
) -> FactorResearchRun:
    """Evaluate a bounded candidate set on train/validation only."""

    if charter.paper_only is not True:
        raise ValueError("factor research must remain paper-only")
    limits = limits or {}
    budget = min(charter.max_experiments, int(limits.get("max_rounds", charter.iteration_budget)))
    if budget < 1:
        raise ValueError("factor research budget must be positive")
    ordered = sorted(candidates, key=lambda item: item.candidate_id)[:budget]
    frame = _frame(dataset)
    spec = _phase_spec(charter, frame, "validation")
    rounds: list[FactorResearchRound] = []
    for index, candidate in enumerate(ordered, start=1):
        evaluation = evaluate_factor_candidate(candidate, _frame(dataset), _forward(dataset), spec)
        admission = build_factor_admission(evaluation, {**dict(charter.hard_constraints), "phase": "validation"})
        training = evaluate_factor_candidate(candidate, frame, _forward(dataset), _phase_spec(charter, frame, "train"))
        rounds.append(FactorResearchRound(index, candidate, evaluation, admission, training))
    state = FactorResearchState.CANDIDATE_POOL if any(item.admission.status == "ADMITTED" for item in rounds) else FactorResearchState.REJECTED
    return FactorResearchRun(charter=charter, state=state, rounds=tuple(rounds))
