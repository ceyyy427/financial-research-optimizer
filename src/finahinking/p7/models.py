"""Typed, privacy-first P7 domain contracts.

These records contain no authorization decisions or executable content. The
repository is the authority for ownership, permissions and persistence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def _payload(value: Any, label: str = "payload") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a JSON object")
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be JSON-safe") from exc
    if len(encoded) > 100_000:
        raise ValueError(f"{label} is too large")
    return json.loads(encoded)


@dataclass(frozen=True)
class Principal:
    principal_id: str
    display_name: str
    status: str = "active"

    def __post_init__(self) -> None:
        object.__setattr__(self, "principal_id", _text(self.principal_id, "principal_id"))
        object.__setattr__(self, "display_name", _text(self.display_name, "display_name"))
        if self.status not in {"active", "suspended", "deleted"}:
            raise ValueError("principal status is invalid")


@dataclass(frozen=True)
class PersonalNode:
    node_id: str
    node_type: str
    title: str
    payload: dict[str, Any]
    privacy_scope: str = "PRIVATE"

    def __post_init__(self) -> None:
        for name in ("node_id", "node_type", "title"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        allowed = {"concept", "claim", "evidence", "event", "question", "hypothesis", "research", "quant_run", "strategy", "feature", "paper_run", "learning_card", "misconception", "review_item", "note"}
        if self.node_type not in allowed:
            raise ValueError("node_type is invalid")
        if self.privacy_scope != "PRIVATE":
            raise ValueError("personal nodes are private by default")
        object.__setattr__(self, "payload", _payload(self.payload))


@dataclass(frozen=True)
class PersonalEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("edge_id", "from_node_id", "to_node_id", "relation_type"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        allowed = {"LEARNED", "USED", "QUESTIONED", "TESTED", "CONFUSED_WITH", "CORRECTED_BY", "DERIVED_FROM", "RELATED_TO", "NEEDS_REVIEW", "MASTERED_EVIDENCE", "SUPPORTED_BY"}
        if self.relation_type not in allowed:
            raise ValueError("relation_type is invalid")
        object.__setattr__(self, "evidence_ids", tuple(_text(item, "evidence_id") for item in self.evidence_ids))


@dataclass(frozen=True)
class MasteryEvidence:
    evidence_id: str
    concept_id: str
    evidence_type: str
    evidence_reference: str
    outcome: str
    observed_at: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("evidence_id", "concept_id", "evidence_type", "evidence_reference", "outcome", "observed_at"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        allowed_types = {"quiz_response", "prediction_response", "explanation", "research_use", "strategy_use", "misconception_correction", "transfer_question", "repeat_exposure"}
        if self.evidence_type not in allowed_types:
            raise ValueError("mastery evidence type is invalid")
        if self.outcome not in {"correct", "incorrect", "neutral", "corrected"}:
            raise ValueError("mastery outcome is invalid")
        object.__setattr__(self, "details", _payload(self.details, "details"))


@dataclass(frozen=True)
class ConceptMasteryState:
    concept_id: str
    state: str
    evidence_count: int
    evidence_ids: tuple[str, ...]
    explanation: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "concept_id", _text(self.concept_id, "concept_id"))
        if self.state not in {"NEW", "EXPOSED", "DEVELOPING", "APPLIED", "ROBUST", "NEEDS_REVIEW"}:
            raise ValueError("mastery state is invalid")
        if self.evidence_count < 0 or self.evidence_count != len(self.evidence_ids):
            raise ValueError("mastery evidence count is inconsistent")
        object.__setattr__(self, "evidence_ids", tuple(_text(item, "evidence_id") for item in self.evidence_ids))
        object.__setattr__(self, "explanation", _text(self.explanation, "explanation"))


@dataclass(frozen=True)
class LearningThread:
    thread_id: str
    title: str
    node_ids: tuple[str, ...]
    status: str = "active"

    def __post_init__(self) -> None:
        object.__setattr__(self, "thread_id", _text(self.thread_id, "thread_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "node_ids", tuple(_text(item, "node_id") for item in self.node_ids))
        if self.status not in {"active", "completed", "archived"}:
            raise ValueError("learning thread status is invalid")


@dataclass(frozen=True)
class ProjectionSpec:
    projection_id: str
    source_kind: str
    source_id: str
    source_fingerprint: str
    fields: tuple[str, ...]
    visibility: str = "PRIVATE"
    version: int = 1
    limitations: tuple[str, ...] = ()
    room_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("projection_id", "source_kind", "source_id", "source_fingerprint"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "fields", tuple(_text(item, "field") for item in self.fields))
        if not self.fields:
            raise ValueError("projection fields are required")
        if self.visibility not in {"PRIVATE", "SHARED_ROOM", "SHARED_GROUP", "PUBLIC"}:
            raise ValueError("projection visibility is invalid")
        if self.version < 1:
            raise ValueError("projection version must be positive")
        object.__setattr__(self, "limitations", tuple(_text(item, "limitation") for item in self.limitations))
        if self.room_id is not None:
            object.__setattr__(self, "room_id", _text(self.room_id, "room_id"))
        if self.visibility == "SHARED_ROOM" and self.room_id is None:
            raise ValueError("room_id is required for a room projection")


@dataclass(frozen=True)
class PublicProjection:
    projection_id: str
    owner_id: str
    visibility: str
    status: str
    version: int
    payload: dict[str, Any]
    source_fingerprint: str
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommunityRoom:
    room_id: str
    name: str
    description: str
    slug: str | None = None

    def __post_init__(self) -> None:
        for name in ("room_id", "name", "description"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "slug", _text(self.slug or self.room_id, "slug"))


@dataclass(frozen=True)
class CommunityPost:
    post_id: str
    room_id: str
    author_id: str
    claim_type: str
    title: str
    body: str
    status: str = "active"

    def __post_init__(self) -> None:
        for name in ("post_id", "room_id", "author_id", "title", "body"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.claim_type not in {"FACT", "INTERPRETATION", "HYPOTHESIS", "QUANT_FINDING", "UNKNOWN", "LIMITATION"}:
            raise ValueError("claim_type is invalid")
        if self.status not in {"active", "removed"}:
            raise ValueError("post status is invalid")


@dataclass(frozen=True)
class CommunityComment:
    comment_id: str
    post_id: str
    author_id: str
    body: str
    status: str = "active"

    def __post_init__(self) -> None:
        for name in ("comment_id", "post_id", "author_id", "body"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if self.status not in {"active", "removed"}:
            raise ValueError("comment status is invalid")


__all__ = [
    "CommunityComment", "CommunityPost", "CommunityRoom", "ConceptMasteryState",
    "LearningThread", "MasteryEvidence", "PersonalEdge", "PersonalNode",
    "Principal", "ProjectionSpec", "PublicProjection",
]
