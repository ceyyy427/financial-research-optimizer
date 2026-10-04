"""Explicit temporal, revision, and conflict semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import ObservationVersion, RevisionStatus


def _parse(value: str, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include a timezone")
    return parsed


def validate_temporal_order(*, occurred_at: str | None, effective_at: str | None, published_at: str | None, available_at: str | None, retrieved_at: str | None) -> bool:
    """Validate the non-inferred ordering of source times.

    ``published_at`` and ``available_at`` may be unknown.  If availability is
    known it must have a publication bound; retrieval is always the final local
    observation time.
    """

    values: list[tuple[str, str]] = []
    for label, value in (("occurred_at", occurred_at), ("effective_at", effective_at), ("published_at", published_at), ("available_at", available_at), ("retrieved_at", retrieved_at)):
        if value is not None:
            values.append((label, value))
    parsed = {label: _parse(value, label) for label, value in values}
    if "effective_at" in parsed and "occurred_at" in parsed and parsed["effective_at"] < parsed["occurred_at"]:
        raise ValueError("temporal order requires effective_at >= occurred_at")
    if "published_at" in parsed and "effective_at" in parsed and parsed["published_at"] < parsed["effective_at"]:
        raise ValueError("temporal order requires published_at >= effective_at")
    if "available_at" in parsed and "published_at" not in parsed:
        raise ValueError("temporal order: available_at requires a published_at bound")
    if "available_at" in parsed and "published_at" in parsed and parsed["available_at"] < parsed["published_at"]:
        raise ValueError("temporal order: available_at cannot precede published_at")
    if "retrieved_at" in parsed and "available_at" in parsed and parsed["retrieved_at"] < parsed["available_at"]:
        raise ValueError("temporal order: retrieved_at cannot precede available_at")
    return True


@dataclass(frozen=True)
class ObservationConflict:
    observation_id: str
    version_a: str
    value_a: float
    version_b: str
    value_b: float
    reason: str
    status: str = "SOURCE_CONFLICT"

    def to_dict(self) -> dict[str, Any]:
        return {"observation_id": self.observation_id, "version_a": self.version_a, "value_a": self.value_a, "version_b": self.version_b, "value_b": self.value_b, "reason": self.reason, "status": self.status}


def record_revision(previous: ObservationVersion, revised: ObservationVersion) -> ObservationVersion:
    if not isinstance(previous, ObservationVersion) or not isinstance(revised, ObservationVersion):
        raise TypeError("revisions require ObservationVersion records")
    if revised.version_id == previous.version_id:
        raise ValueError("revised version must have a new id")
    if revised.capture_id == previous.capture_id and revised.value == previous.value:
        raise ValueError("revision must change the capture or value")
    return ObservationVersion(
        version_id=revised.version_id,
        value=revised.value,
        unit=revised.unit,
        occurred_at=revised.occurred_at,
        effective_at=revised.effective_at,
        published_at=revised.published_at,
        available_at=revised.available_at,
        retrieved_at=revised.retrieved_at,
        capture_id=revised.capture_id,
        revision_status=RevisionStatus.REVISED,
        supersedes_version_id=previous.version_id,
        footnotes=revised.footnotes,
    )


def record_conflict(observation_id: str, first: ObservationVersion, second: ObservationVersion, *, reason: str) -> ObservationConflict:
    if not isinstance(first, ObservationVersion) or not isinstance(second, ObservationVersion):
        raise TypeError("conflicts require ObservationVersion records")
    if first.value == second.value and first.unit == second.unit:
        raise ValueError("identical values do not form a source conflict")
    return ObservationConflict(observation_id, first.version_id, first.value, second.version_id, second.value, reason)


__all__ = ["ObservationConflict", "record_conflict", "record_revision", "validate_temporal_order"]
