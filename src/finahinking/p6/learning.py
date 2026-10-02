"""Small, evidence-grounded learning records for guided quant sessions."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

from .security import validate_payload, validate_untrusted_text


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return copy.deepcopy(value)


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(item) for item in value]
    return copy.deepcopy(value)


@dataclass(frozen=True)
class LearningCard:
    concept: str
    definition: str
    formula: str
    result_context: Mapping[str, Any]
    limitation: str
    evidence_reference: str
    misconception: str | None = None
    interpretation: str | None = None
    common_misconception: str | None = None
    follow_up_question: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("concept", "definition", "limitation", "evidence_reference"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
            validate_untrusted_text(getattr(self, field_name))
        if not isinstance(self.formula, str):
            raise TypeError("formula must be text")
        validate_untrusted_text(self.formula)
        if not isinstance(self.result_context, Mapping):
            raise TypeError("result_context must be a mapping")
        validate_payload(self.result_context)
        object.__setattr__(self, "result_context", _freeze(self.result_context))
        context_reference = self.result_context.get("evidence_reference")
        if context_reference is not None and str(context_reference) != self.evidence_reference:
            raise ValueError("result_context evidence_reference must match the card")
        for field_name in ("misconception", "interpretation", "common_misconception", "follow_up_question"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _text(value, field_name))
                validate_untrusted_text(getattr(self, field_name))
        # Keep the original ``misconception`` spelling as a backwards-
        # compatible alias for the contract's ``common_misconception`` field.
        if self.common_misconception is None and self.misconception is not None:
            object.__setattr__(self, "common_misconception", self.misconception)
        elif self.misconception is None and self.common_misconception is not None:
            object.__setattr__(self, "misconception", self.common_misconception)

    def to_dict(self) -> dict[str, Any]:
        payload = {"concept": self.concept, "definition": self.definition, "formula": self.formula,
                   "result_context": _thaw(self.result_context), "limitation": self.limitation,
                   "evidence_reference": self.evidence_reference}
        if self.misconception:
            payload["misconception"] = self.misconception
        if self.interpretation:
            payload["interpretation"] = self.interpretation
        if self.common_misconception:
            payload["common_misconception"] = self.common_misconception
        if self.follow_up_question:
            payload["follow_up_question"] = self.follow_up_question
        return payload

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Quiz:
    prompt: str
    options: tuple[str, ...]
    correct_answer: str
    evidence_reference: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "prompt", _text(self.prompt, "prompt"))
        object.__setattr__(self, "options", tuple(_text(item, "option") for item in self.options))
        object.__setattr__(self, "correct_answer", _text(self.correct_answer, "correct_answer"))
        object.__setattr__(self, "evidence_reference", _text(self.evidence_reference, "evidence_reference"))
        if self.correct_answer not in self.options:
            raise ValueError("correct_answer must be one of options")

    def to_dict(self) -> dict[str, Any]:
        return {"prompt": self.prompt, "options": list(self.options), "correct_answer": self.correct_answer,
                "evidence_reference": self.evidence_reference}


@dataclass(frozen=True)
class ConceptProgress:
    user_id: str
    concept_id: str
    encounters: int = 0
    correct_responses: int = 0
    incorrect_responses: int = 0
    confidence: float = 0.0
    last_review: str | None = None
    next_review: str | None = None
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("user_id", "concept_id"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if min(self.encounters, self.correct_responses, self.incorrect_responses) < 0:
            raise ValueError("progress counts cannot be negative")
        if not 0 <= float(self.confidence) <= 1:
            raise ValueError("confidence must be between zero and one")
        object.__setattr__(self, "evidence_references", tuple(str(v) for v in self.evidence_references))

    def to_dict(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "concept_id": self.concept_id, "encounters": self.encounters,
                "correct_responses": self.correct_responses, "incorrect_responses": self.incorrect_responses,
                "confidence": self.confidence, "last_review": self.last_review, "next_review": self.next_review,
                "evidence_references": list(self.evidence_references)}

    @property
    def last_seen_at(self) -> str | None:
        return self.last_review

    @property
    def next_review_at(self) -> str | None:
        return self.next_review

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class Misconception:
    user_id: str
    concept_id: str
    observed_statement: str
    correction: str
    evidence_reference: str

    def __post_init__(self) -> None:
        for name in ("user_id", "concept_id", "observed_statement", "correction", "evidence_reference"):
            object.__setattr__(self, name, _text(getattr(self, name), name))

    def to_dict(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "concept_id": self.concept_id,
                "observed_statement": self.observed_statement, "correction": self.correction,
                "evidence_reference": self.evidence_reference}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class ReviewItem:
    user_id: str
    concept_id: str
    due_at: str | None = None
    evidence_reference: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_id", _text(self.user_id, "user_id"))
        object.__setattr__(self, "concept_id", _text(self.concept_id, "concept_id"))
        if self.due_at is not None:
            object.__setattr__(self, "due_at", _text(self.due_at, "due_at"))
        if self.evidence_reference is not None:
            object.__setattr__(self, "evidence_reference", _text(self.evidence_reference, "evidence_reference"))

    def to_dict(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "concept_id": self.concept_id,
                "due_at": self.due_at, "evidence_reference": self.evidence_reference}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class LearningThread:
    user_id: str
    concept_ids: tuple[str, ...]
    evidence_references: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_id", _text(self.user_id, "user_id"))
        object.__setattr__(self, "concept_ids", tuple(_text(v, "concept_id") for v in self.concept_ids))
        object.__setattr__(self, "evidence_references", tuple(_text(v, "evidence_reference") for v in self.evidence_references))

    def to_dict(self) -> dict[str, Any]:
        return {"user_id": self.user_id, "concept_ids": list(self.concept_ids),
                "evidence_references": list(self.evidence_references)}

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


def make_learning_card(*, concept: str, definition: str, formula: str = "", result_context: dict[str, Any], limitation: str, evidence_reference: str | None = None, interpretation: str | None = None, misconception: str | None = None, common_misconception: str | None = None, follow_up_question: str | None = None) -> LearningCard:
    context = copy.deepcopy(result_context)
    evidence = evidence_reference or context.get("evidence_reference")
    if not evidence:
        raise ValueError("result_context must include evidence_reference")
    resolved_interpretation = interpretation if interpretation is not None else context.get("interpretation")
    resolved_misconception = misconception if misconception is not None else context.get("misconception")
    resolved_common = common_misconception if common_misconception is not None else context.get("common_misconception")
    resolved_follow_up = follow_up_question if follow_up_question is not None else context.get("follow_up_question")
    return LearningCard(concept, definition, formula, context, limitation, str(evidence),
                        misconception=resolved_misconception,
                        interpretation=resolved_interpretation,
                        common_misconception=resolved_common,
                        follow_up_question=resolved_follow_up)


def generate_quiz(card: LearningCard) -> Quiz:
    if not isinstance(card, LearningCard):
        raise TypeError("card must be a LearningCard")
    correct = card.definition
    options = (correct, "A guarantee of future performance", "A trading instruction")
    return Quiz(f"Which statement best defines {card.concept}?", options, correct, card.evidence_reference)


def record_misconception(user_id: str, card: LearningCard, *, observed_statement: str) -> Misconception:
    if not isinstance(card, LearningCard):
        raise TypeError("card must be a LearningCard")
    observed = _text(observed_statement, "observed_statement")
    validate_untrusted_text(observed)
    return Misconception(_text(user_id, "user_id"), card.concept, observed, card.definition, card.evidence_reference)


class LearningStore:
    def __init__(self) -> None:
        self._progress: dict[tuple[str, str], ConceptProgress] = {}
        self._misconceptions: list[Misconception] = []
        self._review_items: list[ReviewItem] = []
        self._threads: list[LearningThread] = []

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def record_encounter(self, user_id: str, card: LearningCard, *, confidence: float = 0.0) -> ConceptProgress:
        """Record that a card was shown without inventing a quiz answer.

        A workflow that has not received a user answer must not mark the
        concept as incorrect.  This method updates only encounter metadata.
        """

        if not isinstance(card, LearningCard):
            raise TypeError("card must be a LearningCard")
        key = (_text(user_id, "user_id"), card.concept)
        current = self._progress.get(key, ConceptProgress(key[0], key[1]))
        current = replace(
            current,
            encounters=current.encounters + 1,
            confidence=float(confidence),
            last_review=self._now(),
            evidence_references=tuple(dict.fromkeys((*current.evidence_references, card.evidence_reference))),
        )
        self._progress[key] = current
        return current

    def record_answer(self, user_id: str, card: LearningCard, *, correct: bool, confidence: float = 0.0) -> ConceptProgress:
        if not isinstance(card, LearningCard):
            raise TypeError("card must be a LearningCard")
        if not isinstance(correct, bool):
            raise TypeError("correct must be boolean")
        key = (_text(user_id, "user_id"), card.concept)
        current = self._progress.get(key, ConceptProgress(key[0], key[1]))
        current = replace(current, encounters=current.encounters + 1,
                          correct_responses=current.correct_responses + int(correct),
                          incorrect_responses=current.incorrect_responses + int(not correct),
                          confidence=float(confidence), last_review=self._now(),
                          evidence_references=tuple(dict.fromkeys((*current.evidence_references, card.evidence_reference))))
        self._progress[key] = current
        return current

    def get_progress(self, user_id: str, concept_id: str) -> ConceptProgress | None:
        return self._progress.get((_text(user_id, "user_id"), _text(concept_id, "concept_id")))

    @property
    def misconceptions(self) -> tuple[Misconception, ...]:
        return tuple(self._misconceptions)

    def add_misconception(self, record: Misconception) -> Misconception:
        if not isinstance(record, Misconception):
            raise TypeError("record must be a Misconception")
        self._misconceptions.append(record)
        return record

    @property
    def review_items(self) -> tuple[ReviewItem, ...]:
        return tuple(self._review_items)

    def add_review_item(self, item: ReviewItem) -> ReviewItem:
        if not isinstance(item, ReviewItem):
            raise TypeError("item must be a ReviewItem")
        self._review_items.append(item)
        return item

    @property
    def threads(self) -> tuple[LearningThread, ...]:
        return tuple(self._threads)

    def add_thread(self, thread: LearningThread) -> LearningThread:
        if not isinstance(thread, LearningThread):
            raise TypeError("thread must be a LearningThread")
        self._threads.append(thread)
        return thread


__all__ = ["ConceptProgress", "LearningCard", "LearningStore", "LearningThread", "Misconception", "Quiz", "ReviewItem", "generate_quiz", "make_learning_card", "record_misconception"]
