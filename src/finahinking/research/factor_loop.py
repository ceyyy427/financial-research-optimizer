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

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_index": self.round_index,
            "candidate": self.candidate.to_dict(),
            "evaluation": self.evaluation.to_dict(),
            "admission": self.admission.to_dict(),
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
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "charter": self.charter.to_dict(),
            "state": self.state.value,
            "rounds": [item.to_dict() for item in self.rounds],
            "selected_candidate": self.selected_candidate,
            "test_evaluation": None if self.test_evaluation is None else self.test_evaluation.to_dict(),
            "fingerprint": _digest({"charter": self.charter.to_dict(), "state": self.state.value, "rounds": [item.to_dict() for item in self.rounds], "selected_candidate": self.selected_candidate}),
        }

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
            {**dict(self.charter.hard_constraints), "phase": "test", "oos": True},
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
    spec = {**dict(charter.hard_constraints), "phase": "validation", "oos": False}
    rounds: list[FactorResearchRound] = []
    for index, candidate in enumerate(ordered, start=1):
        evaluation = evaluate_factor_candidate(candidate, _frame(dataset), _forward(dataset), spec)
        admission = build_factor_admission(evaluation, {**dict(charter.hard_constraints), "phase": "validation"})
        rounds.append(FactorResearchRound(index, candidate, evaluation, admission))
    state = FactorResearchState.CANDIDATE_POOL if any(item.admission.status == "ADMITTED" for item in rounds) else FactorResearchState.REJECTED
    return FactorResearchRun(charter=charter, state=state, rounds=tuple(rounds))

