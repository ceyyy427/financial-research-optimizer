"""Immutable audit trail for a guided P6 session."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


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
class GuidedSessionAudit:
    user_question: str
    user_id: str | None = None
    classification: str | None = None
    hypothesis: str | None = None
    experiment_specification: dict[str, Any] | None = None
    assumptions: tuple[str, ...] = ()
    tool_calls: tuple[str, ...] = ()
    research_run_ids: tuple[str, ...] = ()
    quant_run_ids: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    explanation_version: str | None = None
    state: str = "QUESTION_RECEIVED"
    created_at: str = ""
    artifact_ids: tuple[str, ...] = ()
    result_fingerprints: tuple[str, ...] = ()
    decision_log: tuple[dict[str, Any], ...] = ()
    learning_events: tuple[dict[str, Any], ...] = ()
    prediction_events: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "user_question", _text(self.user_question, "user_question"))
        if self.user_id is not None:
            object.__setattr__(self, "user_id", _text(self.user_id, "user_id"))
        if self.experiment_specification is not None:
            if not isinstance(self.experiment_specification, Mapping):
                raise TypeError("experiment_specification must be a mapping")
            object.__setattr__(self, "experiment_specification", _freeze(self.experiment_specification))
        for name in (
            "assumptions", "tool_calls", "research_run_ids", "quant_run_ids",
            "evidence_references", "warnings", "limitations", "artifact_ids",
            "result_fingerprints",
        ):
            object.__setattr__(self, name, tuple(str(value) for value in getattr(self, name)))
        for name in ("decision_log", "learning_events", "prediction_events"):
            events = getattr(self, name)
            if not isinstance(events, tuple):
                events = tuple(events)
            if any(not isinstance(event, Mapping) for event in events):
                raise TypeError(f"{name} must contain mappings")
            object.__setattr__(self, name, tuple(_freeze(event) for event in events))
        object.__setattr__(self, "state", _text(self.state, "state"))
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now(UTC).isoformat())

    @classmethod
    def start(cls, user_question: str, *, user_id: str | None = None, created_at: str | None = None) -> GuidedSessionAudit:
        return cls(user_question=_text(user_question, "user_question"), user_id=user_id,
                   created_at=created_at or datetime.now(UTC).isoformat())

    def record_classification(self, category: Any) -> GuidedSessionAudit:
        value = getattr(category, "value", category)
        return replace(self, classification=str(value), state="CLASSIFIED",
                       decision_log=(*self.decision_log, {"kind": "classification", "value": str(value)}))

    def record_hypothesis(self, hypothesis: Any) -> GuidedSessionAudit:
        value = getattr(hypothesis, "statement", hypothesis)
        return replace(self, hypothesis=str(value), state="HYPOTHESIS_PROPOSED",
                       decision_log=(*self.decision_log, {"kind": "hypothesis", "value": str(value)}))

    def record_experiment(self, specification: Any) -> GuidedSessionAudit:
        payload = specification.to_dict() if hasattr(specification, "to_dict") else dict(specification)
        return replace(self, experiment_specification=copy.deepcopy(payload), state="EXPERIMENT_PROPOSED",
                       decision_log=(*self.decision_log, {"kind": "experiment", "fingerprint": payload.get("fingerprint")}))

    def record_assumptions(self, assumptions: Any) -> GuidedSessionAudit:
        accepted = tuple(str(v) for v in assumptions)
        return replace(self, assumptions=accepted, state="ASSUMPTIONS_ACCEPTED",
                       decision_log=(*self.decision_log, {"kind": "assumptions_accepted", "values": list(accepted)}))

    def record_tool_call(
        self,
        tool_name: str,
        *,
        request_id: str | None = None,
        request_fingerprint: str | None = None,
        experiment_fingerprint: str | None = None,
        status: str | None = None,
    ) -> GuidedSessionAudit:
        name = _text(tool_name, "tool_name")
        decision = {"kind": "tool_call", "tool_name": name}
        if request_id is not None:
            decision["request_id"] = _text(request_id, "request_id")
        if request_fingerprint is not None:
            decision["request_fingerprint"] = _text(request_fingerprint, "request_fingerprint")
        if experiment_fingerprint is not None:
            decision["experiment_fingerprint"] = _text(experiment_fingerprint, "experiment_fingerprint")
        if status is not None:
            decision["status"] = _text(status, "status")
        return replace(self, tool_calls=(*self.tool_calls, name), state="TOOL_EXECUTED",
                       decision_log=(*self.decision_log, decision))

    def record_evidence(
        self,
        evidence_reference: str,
        *,
        research_run_id: str | None = None,
        quant_run_id: str | None = None,
        artifact_id: str | None = None,
        result_fingerprint: str | None = None,
        evidence_kind: str | None = None,
        warnings: tuple[str, ...] = (),
        limitations: tuple[str, ...] = (),
    ) -> GuidedSessionAudit:
        evidence_reference = _text(evidence_reference, "evidence_reference")
        inferred_quant_ids = self.quant_run_ids
        if quant_run_id:
            inferred_quant_ids = (*inferred_quant_ids, quant_run_id)
        elif evidence_reference.startswith("quant-"):
            inferred_quant_ids = (*inferred_quant_ids, evidence_reference)
        inferred_artifacts = self.artifact_ids
        if artifact_id:
            inferred_artifacts = (*inferred_artifacts, _text(artifact_id, "artifact_id"))
        elif evidence_reference.startswith("artifact-"):
            inferred_artifacts = (*inferred_artifacts, evidence_reference)
        inferred_results = self.result_fingerprints
        if result_fingerprint:
            inferred_results = (*inferred_results, _text(result_fingerprint, "result_fingerprint"))
        decision = {"kind": "evidence", "reference": evidence_reference}
        if evidence_kind:
            decision["evidence_kind"] = _text(evidence_kind, "evidence_kind")
        return replace(self,
                       evidence_references=(*self.evidence_references, evidence_reference),
                       research_run_ids=(*self.research_run_ids, research_run_id) if research_run_id else self.research_run_ids,
                       quant_run_ids=inferred_quant_ids,
                       artifact_ids=inferred_artifacts,
                       result_fingerprints=inferred_results,
                       warnings=tuple(dict.fromkeys((*self.warnings, *(str(v) for v in warnings)))),
                       limitations=tuple(dict.fromkeys((*self.limitations, *(str(v) for v in limitations)))),
                       decision_log=(*self.decision_log, decision),
                       state="EVIDENCE_READY")

    def record_explanation(self, version: str = "p6-explanation-v1") -> GuidedSessionAudit:
        return replace(self, explanation_version=_text(version, "explanation_version"), state="EXPLANATION_READY",
                       decision_log=(*self.decision_log, {"kind": "explanation", "version": version}))

    def record_learning(self, *, concept_id: str | None = None, card_fingerprint: str | None = None, event: str = "card_created") -> GuidedSessionAudit:
        learning_event: dict[str, Any] = {"event": _text(event, "event")}
        if concept_id is not None:
            learning_event["concept_id"] = _text(concept_id, "concept_id")
        if card_fingerprint is not None:
            learning_event["card_fingerprint"] = _text(card_fingerprint, "card_fingerprint")
        return replace(self, state="LEARNING_READY",
                       learning_events=(*self.learning_events, learning_event),
                       decision_log=(*self.decision_log, {"kind": "learning", **learning_event}))

    def record_terminal(self, state: str, *, reason: str) -> GuidedSessionAudit:
        terminal = _text(state, "state")
        return replace(self, state=terminal,
                       decision_log=(*self.decision_log, {"kind": "terminal", "state": terminal,
                                                         "reason": _text(reason, "reason")}))

    def record_prediction(self, prediction: str, *, evidence_reference: str | None = None) -> GuidedSessionAudit:
        event: dict[str, Any] = {"phase": "PREDICT", "prediction": _text(prediction, "prediction")}
        if evidence_reference is not None:
            event["evidence_reference"] = _text(evidence_reference, "evidence_reference")
        return replace(self, prediction_events=(*self.prediction_events, event),
                       decision_log=(*self.decision_log, {"kind": "prediction", **event}))

    def record_reveal(self, result_fingerprint: str, *, evidence_reference: str) -> GuidedSessionAudit:
        event = {"phase": "REVEAL", "result_fingerprint": _text(result_fingerprint, "result_fingerprint"),
                 "evidence_reference": _text(evidence_reference, "evidence_reference")}
        return replace(self, prediction_events=(*self.prediction_events, event),
                       decision_log=(*self.decision_log, {"kind": "reveal", **event}))

    @property
    def artifacts(self) -> tuple[str, ...]:
        """Alias used by clients that refer to artifact records generically."""

        return self.artifact_ids

    def to_dict(self) -> dict[str, Any]:
        payload = {"user_question": self.user_question, "user_id": self.user_id, "classification": self.classification,
                   "hypothesis": self.hypothesis, "experiment_specification": _thaw(self.experiment_specification),
                   "assumptions": list(self.assumptions), "tool_calls": list(self.tool_calls),
                   "research_run_ids": list(self.research_run_ids), "quant_run_ids": list(self.quant_run_ids),
                   "evidence_references": list(self.evidence_references), "warnings": list(self.warnings),
                   "limitations": list(self.limitations), "explanation_version": self.explanation_version,
                   "state": self.state, "artifact_ids": list(self.artifact_ids),
                   "result_fingerprints": list(self.result_fingerprints),
                   "decision_log": _thaw(self.decision_log),
                   "learning_events": _thaw(self.learning_events),
                   "prediction_events": _thaw(self.prediction_events),
                   "created_at": self.created_at}
        payload["fingerprint"] = _digest(payload)
        return payload

    @property
    def fingerprint(self) -> str:
        return self.to_dict()["fingerprint"]


__all__ = ["GuidedSessionAudit"]
