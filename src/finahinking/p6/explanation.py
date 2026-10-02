"""Grounded, educational explanations for normalized quant evidence."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .grounding import GroundedClaim, claims_from_result
from .security import validate_payload, validate_untrusted_text


@dataclass(frozen=True)
class ExplanationRecord:
    what_was_asked: str
    what_was_tested: str
    data_used: str
    result: str
    supports: str
    does_not_support: str
    limitations: tuple[str, ...]
    concepts: tuple[str, ...]
    claims: tuple[GroundedClaim, ...] = ()
    evidence_reference: str = ""
    version: str = "p6-explanation-v1"
    classification: str | None = None
    warnings: tuple[str, ...] = ()
    source_fingerprints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("what_was_asked", "what_was_tested", "data_used", "result", "supports", "does_not_support"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
            validate_untrusted_text(getattr(self, name))
        if not self.evidence_reference:
            raise ValueError("evidence_reference is required")
        for claim in self.claims:
            if not isinstance(claim, GroundedClaim):
                raise TypeError("claims must be GroundedClaim records")
            if not claim.source_verified:
                raise ValueError("explanation claims require a verified normalized source")
            if claim.evidence_reference != self.evidence_reference:
                raise ValueError("claim evidence reference does not match explanation")
        fingerprints = tuple(dict.fromkeys(claim.source_fingerprint for claim in self.claims))
        if any(not fingerprint for fingerprint in fingerprints):
            raise ValueError("explanation claims require source fingerprints")
        if self.source_fingerprints and tuple(self.source_fingerprints) != fingerprints:
            raise ValueError("source_fingerprints do not match claims")
        object.__setattr__(self, "source_fingerprints", fingerprints)
        object.__setattr__(self, "warnings", tuple(str(value) for value in self.warnings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "what_was_asked": self.what_was_asked,
            "what_was_tested": self.what_was_tested,
            "data_used": self.data_used,
            "result": self.result,
            "supports": self.supports,
            "does_not_support": self.does_not_support,
            "limitations": list(self.limitations),
            "concepts": list(self.concepts),
            "claims": [claim.to_dict() for claim in self.claims],
            "evidence_reference": self.evidence_reference,
            "classification": self.classification,
            "warnings": list(self.warnings),
            "source_fingerprints": list(self.source_fingerprints),
        }


@dataclass(frozen=True)
class PredictionRevealExplain:
    prompt: str
    prediction: str
    result: dict[str, Any]
    explanation: str
    evidence_reference: str
    phase: str = "EXPLAIN"
    result_fingerprint: str | None = None
    events: tuple[str, ...] = ("PREDICT", "REVEAL", "EXPLAIN")
    created_at: str = ""

    def __post_init__(self) -> None:
        if self.phase != "EXPLAIN":
            raise ValueError("interaction must end in EXPLAIN")
        if not self.evidence_reference:
            raise ValueError("evidence_reference is required")
        if not self.created_at:
            object.__setattr__(self, "created_at", datetime.now(UTC).isoformat())
        object.__setattr__(self, "events", tuple(self.events))
        if self.events != ("PREDICT", "REVEAL", "EXPLAIN"):
            raise ValueError("predict/reveal/explain events are required in order")
        inferred = self.result.get("fingerprint") or self.result.get("result_fingerprint")
        if self.result_fingerprint is None and isinstance(inferred, str):
            object.__setattr__(self, "result_fingerprint", inferred)
        if self.result_fingerprint is not None and not re.fullmatch(r"[0-9a-f]{64}", self.result_fingerprint):
            raise ValueError("result_fingerprint is invalid")
        for value, name in ((self.prompt, "prompt"), (self.prediction, "prediction"), (self.explanation, "explanation"), (self.evidence_reference, "evidence_reference")):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
            validate_untrusted_text(value)
        if not isinstance(self.result, dict):
            raise TypeError("result must be a mapping")
        validate_payload(self.result)

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "prompt": self.prompt,
            "prediction": self.prediction,
            "result": copy.deepcopy(self.result),
            "explanation": self.explanation,
            "evidence_reference": self.evidence_reference,
            "result_fingerprint": self.result_fingerprint,
            "events": list(self.events),
            "created_at": self.created_at,
        }


def predict_reveal_explain(
    *, prompt: str, prediction: str, result: dict[str, Any], explanation: str, evidence_reference: str,
    result_fingerprint: str | None = None, require_grounding: bool = False,
) -> PredictionRevealExplain:
    if require_grounding:
        from .grounding import _verify_source

        _verify_source(result, evidence_reference)
        if result_fingerprint and result.get("fingerprint") not in {None, result_fingerprint}:
            raise ValueError("result_fingerprint does not match the normalized result")
    return PredictionRevealExplain(prompt, prediction, copy.deepcopy(result), explanation, evidence_reference,
                                   result_fingerprint=result_fingerprint)


def explain_result(
    *,
    question: str,
    tested: str,
    data_used: str,
    normalized_result: Any,
    evidence_reference: str,
    evidence_kind: str,
    supports: str,
    does_not_support: str,
    limitations: tuple[str, ...] | list[str],
    concepts: tuple[str, ...] | list[str],
    warnings: tuple[str, ...] | list[str] = (),
) -> ExplanationRecord:
    claims = claims_from_result(normalized_result, evidence_reference, evidence_kind)
    metric_text = "; ".join(claim.text for claim in claims) or "No finite metric was available."
    return ExplanationRecord(
        what_was_asked=question,
        what_was_tested=tested,
        data_used=data_used,
        result=metric_text,
        supports=supports,
        does_not_support=does_not_support,
        limitations=tuple(str(item) for item in limitations),
        concepts=tuple(str(item) for item in concepts),
        claims=claims,
        evidence_reference=evidence_reference,
        warnings=tuple(dict.fromkeys((*[str(item) for item in warnings], *[str(item) for item in limitations if str(item).isupper() and "_" in str(item)]))),
    )


__all__ = ["ExplanationRecord", "PredictionRevealExplain", "explain_result", "predict_reveal_explain"]
