"""Evidence-bound quality and learning evaluation for the P6.5 slice.

The quality report is intentionally small and deterministic.  It is a gate
input, not a claim that a source is correct: it checks whether the captured
rows satisfy the declared grain, completeness, numeric, and temporal
contracts before they are allowed into the understanding journey.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp is required")
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


@dataclass(frozen=True)
class DataQualityReport:
    """Auditable checks over a bounded set of canonicalized rows."""

    row_count: int
    grain: str
    required_fields: tuple[str, ...]
    duplicate_keys: int
    missing_by_field: dict[str, int]
    numeric_invalid: int
    temporal_invalid: int
    issues: tuple[str, ...]
    passed: bool

    @classmethod
    def from_rows(
        cls,
        rows: Iterable[Mapping[str, Any]],
        *,
        required_fields: Iterable[str],
        grain_fields: Iterable[str] | None = None,
        numeric_fields: Iterable[str] | None = None,
        temporal_fields: tuple[str, str, str] = ("published_at", "available_at", "retrieved_at"),
    ) -> DataQualityReport:
        normalized_rows = [dict(row) for row in rows]
        if any(not isinstance(row, Mapping) for row in normalized_rows):
            raise TypeError("quality rows must be mappings")
        required = tuple(str(field).strip() for field in required_fields)
        if not required or any(not field for field in required):
            raise ValueError("required_fields must contain text")
        if grain_fields is None:
            if {"series_id", "reference_period"}.issubset(required):
                grain = ("series_id", "reference_period")
            elif len(required) >= 2:
                grain = required[:2]
            else:
                grain = required
        else:
            grain = tuple(str(field).strip() for field in grain_fields)
        if not grain or any(not field for field in grain):
            raise ValueError("grain_fields must contain text")
        numeric = set(numeric_fields or ("value",))
        missing = {field: sum(field not in row or row[field] is None or row[field] == "" for row in normalized_rows) for field in required}
        keys = [tuple(row.get(field) for field in grain) for row in normalized_rows]
        duplicate_keys = sum(count - 1 for count in Counter(keys).values() if count > 1)

        numeric_invalid = 0
        for row in normalized_rows:
            for field in numeric:
                value = row.get(field)
                if value is None:
                    continue  # missingness is reported separately
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    numeric_invalid += 1

        temporal_invalid = 0
        published_field, available_field, retrieved_field = temporal_fields
        for row in normalized_rows:
            try:
                published = _parse_time(row[published_field]) if row.get(published_field) is not None else None
                available = _parse_time(row[available_field]) if row.get(available_field) is not None else None
                retrieved = _parse_time(row[retrieved_field]) if row.get(retrieved_field) is not None else None
                if available is not None and published is None:
                    raise ValueError("available_at has no published_at bound")
                if available is not None and published is not None and available < published:
                    raise ValueError("available_at precedes published_at")
                if retrieved is not None and available is not None and retrieved < available:
                    raise ValueError("retrieved_at precedes available_at")
            except (KeyError, TypeError, ValueError):
                # Missing timestamps are a missingness concern unless the row
                # supplies one half of an impossible temporal relation.
                if any(row.get(field) is not None for field in temporal_fields):
                    temporal_invalid += 1

        issues: list[str] = []
        for field, count in missing.items():
            if count:
                issues.append(f"missing:{field}={count}")
        if duplicate_keys:
            issues.append(f"duplicate_grain={duplicate_keys}")
        if numeric_invalid:
            issues.append(f"numeric_invalid={numeric_invalid}")
        if temporal_invalid:
            issues.append(f"temporal_invalid={temporal_invalid}")
        return cls(
            row_count=len(normalized_rows),
            grain="/".join(grain),
            required_fields=required,
            duplicate_keys=duplicate_keys,
            missing_by_field=missing,
            numeric_invalid=numeric_invalid,
            temporal_invalid=temporal_invalid,
            issues=tuple(issues),
            passed=not issues,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "row_count": self.row_count,
            "grain": self.grain,
            "required_fields": list(self.required_fields),
            "duplicate_keys": self.duplicate_keys,
            "missing_by_field": dict(self.missing_by_field),
            "numeric_invalid": self.numeric_invalid,
            "temporal_invalid": self.temporal_invalid,
            "issues": list(self.issues),
            "passed": self.passed,
        }


def understanding_gain(pre_answers: Iterable[bool], post_answers: Iterable[bool]) -> dict[str, Any]:
    """Return a descriptive pre/post learning proxy.

    This metric deliberately does not estimate a causal treatment effect.  It
    is a transparent count of correct answers around one product journey and
    should be reported with that limitation attached.
    """

    before = tuple(bool(answer) for answer in pre_answers)
    after = tuple(bool(answer) for answer in post_answers)
    if not before or not after:
        raise ValueError("pre and post answer sets must be non-empty")
    if len(before) != len(after):
        raise ValueError("pre and post answer sets must have equal length")
    correct_before = sum(before)
    correct_after = sum(after)
    return {
        "correct_before": correct_before,
        "correct_after": correct_after,
        "gain": correct_after - correct_before,
        "items": len(before),
        "interpretation": "Descriptive pre/post understanding proxy; positive gain means more answers were correct after the journey.",
        "limitation": "This is not a causal estimate: there is no control group, randomization, or correction for retest and selection effects.",
    }


@dataclass(frozen=True)
class EvaluationCheck:
    dimension: str
    name: str
    passed: bool
    evidence: str
    limitation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "name": self.name,
            "passed": self.passed,
            "evidence": self.evidence,
            "limitation": self.limitation,
        }


@dataclass(frozen=True)
class UnderstandingEvaluation:
    checks: tuple[EvaluationCheck, ...]
    understanding_gain: dict[str, Any]
    misconceptions: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def by_dimension(self) -> dict[str, bool]:
        dimensions = {check.dimension for check in self.checks}
        return {dimension: all(check.passed for check in self.checks if check.dimension == dimension) for dimension in dimensions}

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": [check.to_dict() for check in self.checks],
            "dimensions": self.by_dimension(),
            "understanding_gain": dict(self.understanding_gain),
            "misconceptions": list(self.misconceptions),
        }


def _field(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _claim_type(value: Any) -> str | None:
    claim_type = _field(value, "claim_type")
    if claim_type is None:
        return None
    return str(getattr(claim_type, "value", claim_type))


def evaluate_journey(journey: Any, *, pre_answers: Iterable[bool], post_answers: Iterable[bool]) -> UnderstandingEvaluation:
    """Evaluate the three P6.5 quality dimensions without inventing scores.

    The harness checks structural contracts and reports a descriptive
    pre/post proxy.  It intentionally does not turn the result into an
    engagement score or a causal learning estimate.
    """

    if journey is None:
        raise TypeError("journey is required")
    event = _field(journey, "event")
    evidence = tuple(_field(journey, "evidence", ()) or ())
    claims = tuple(_field(journey, "claims", ()) or ())
    evidence_ids = {str(_field(item, "evidence_id")) for item in evidence if _field(item, "evidence_id") is not None}
    event_evidence = set(_field(event, "evidence_ids", ()) or ()) if event is not None else set()
    checks: list[EvaluationCheck] = []

    def add(dimension: str, name: str, passed: bool, evidence_text: str, limitation: str = "") -> None:
        checks.append(EvaluationCheck(dimension, name, bool(passed), evidence_text, limitation))

    # Research quality: source integrity, provenance, timing, quant output.
    add("RESEARCH_QUALITY", "source_integrity", bool(event and event_evidence and event_evidence.issubset(evidence_ids)), "event evidence ids resolve to captured evidence")
    linked_claims = all(
        bool(_field(claim, "source_verified", False))
        and set(_field(claim, "evidence_ids", ()) or ()).issubset(evidence_ids)
        for claim in claims
    )
    add("RESEARCH_QUALITY", "claim_grounding", bool(claims) and linked_claims, "verified claims resolve to the journey evidence")
    published = _field(event, "published_at") if event is not None else None
    available = _field(event, "available_at") if event is not None else None
    temporal_ok = False
    if published and available:
        try:
            temporal_ok = _parse_time(available) >= _parse_time(published)
        except (TypeError, ValueError):
            temporal_ok = False
    add("RESEARCH_QUALITY", "temporal_integrity", temporal_ok, "published_at <= available_at", "An unresolved vintage is not evidence that no revision occurred.")
    quant = _field(journey, "quant_evidence")
    quant_status = _field(quant, "status")
    quant_fingerprint = _field(quant, "result_fingerprint")
    add("RESEARCH_QUALITY", "quant_provenance", quant_status == "SUCCEEDED" and bool(quant_fingerprint), "typed P6 response is successful and fingerprinted")

    # Agent quality: typed distinctions, uncertainty, and interaction order.
    expected_types = {"FACT", "INTERPRETATION", "HYPOTHESIS", "QUANT_FINDING", "UNKNOWN", "LIMITATION"}
    observed_types = {_claim_type(claim) for claim in claims}
    add("AGENT_QUALITY", "claim_taxonomy", expected_types.issubset(observed_types), "fact, interpretation, hypothesis, quant finding, unknown, and limitation are distinct")
    add("AGENT_QUALITY", "uncertainty_disclosure", "UNKNOWN" in observed_types and "LIMITATION" in observed_types, "unknowns and limitations are explicit")
    interaction = _field(journey, "predict_reveal_explain")
    add("AGENT_QUALITY", "predict_reveal_explain", tuple(_field(interaction, "events", ()) or ()) == ("PREDICT", "REVEAL", "EXPLAIN"), "learning interaction preserves ordered phases")

    # Learning quality: concepts, misconception correction, and transfer.
    bridge = _field(journey, "knowledge_bridge")
    card = _field(journey, "learning_card")
    add("LEARNING_QUALITY", "knowledge_bridge", bool(bridge), "event maps to concepts and mechanism relations")
    add("LEARNING_QUALITY", "evidence_bound_card", bool(_field(card, "evidence_reference")), "learning card points to evidence")
    misconception = _field(card, "common_misconception") or _field(card, "misconception")
    follow_up = _field(card, "follow_up_question")
    add("LEARNING_QUALITY", "misconception_and_transfer", bool(misconception and follow_up), "card names a misconception and asks what evidence could change the view")

    gain = understanding_gain(pre_answers, post_answers)
    return UnderstandingEvaluation(tuple(checks), gain, (str(misconception),) if misconception else ())


__all__ = ["DataQualityReport", "EvaluationCheck", "UnderstandingEvaluation", "evaluate_journey", "understanding_gain"]
