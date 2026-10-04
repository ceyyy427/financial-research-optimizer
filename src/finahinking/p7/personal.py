"""Owner-scoped personal continuity services for P7.

The repository is the authorization boundary.  This module only composes its
private records into explicit, inspectable contracts; it never infers an
unrelated profile and it never changes a quantitative or factual artifact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .models import MasteryEvidence, PersonalEdge, PersonalNode


def _text(value: Any, label: str, *, limit: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    value = value.strip()
    if len(value) > limit:
        raise ValueError(f"{label} is too long")
    return value


def _timestamp(value: Any, label: str) -> str:
    return _text(value, label, limit=80)


@dataclass(frozen=True)
class MisconceptionContinuity:
    """A private, evidence-linked misconception lifecycle.

    ``status`` describes an interaction record (not a psychological label),
    and ``corrected_at`` is set only by an explicit correction event.
    """

    misconception_id: str
    concept_id: str
    observed_statement: str
    correction: str
    evidence_reference: str
    detected_at: str
    corrected_at: str | None = None
    status: str = "OPEN"
    related_concept_ids: tuple[str, ...] = ()
    learning_interactions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("misconception_id", "concept_id", "observed_statement", "correction", "evidence_reference"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "detected_at", _timestamp(self.detected_at, "detected_at"))
        if self.corrected_at is not None:
            object.__setattr__(self, "corrected_at", _timestamp(self.corrected_at, "corrected_at"))
        if self.status not in {"OPEN", "CORRECTED"}:
            raise ValueError("misconception status must be OPEN or CORRECTED")
        if self.status == "CORRECTED" and self.corrected_at is None:
            raise ValueError("corrected misconception requires corrected_at")
        if self.status == "OPEN" and self.corrected_at is not None:
            raise ValueError("open misconception cannot have corrected_at")
        object.__setattr__(self, "related_concept_ids", tuple(_text(item, "related_concept_id") for item in self.related_concept_ids))
        object.__setattr__(self, "learning_interactions", tuple(_text(item, "learning_interaction") for item in self.learning_interactions))

    @classmethod
    def from_node(cls, node: PersonalNode) -> MisconceptionContinuity:
        if node.node_type != "misconception":
            raise TypeError("node is not a misconception")
        payload = node.payload
        return cls(
            node.node_id,
            str(payload["concept_id"]),
            str(payload["observed_statement"]),
            str(payload["correction"]),
            str(payload["evidence_reference"]),
            str(payload["detected_at"]),
            str(payload["corrected_at"]) if payload.get("corrected_at") else None,
            str(payload.get("status", "OPEN")),
            tuple(str(item) for item in payload.get("related_concept_ids", ())),
            tuple(str(item) for item in payload.get("learning_interactions", ())),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "observed_statement": self.observed_statement,
            "correction": self.correction,
            "evidence_reference": self.evidence_reference,
            "detected_at": self.detected_at,
            "corrected_at": self.corrected_at,
            "status": self.status,
            "related_concept_ids": list(self.related_concept_ids),
            "learning_interactions": list(self.learning_interactions),
        }


@dataclass(frozen=True)
class TimelineEvent:
    """One inspectable private timeline item with source provenance."""

    event_id: str
    owner_id: str
    kind: str
    object_id: str
    title: str
    occurred_at: str
    source_kind: str = ""
    source_id: str = ""
    source_fingerprint: str = ""
    evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    privacy_scope: str = "PRIVATE"

    def __post_init__(self) -> None:
        for name in ("event_id", "owner_id", "kind", "object_id", "title", "occurred_at"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        for name in ("source_kind", "source_id", "source_fingerprint"):
            value = getattr(self, name)
            if value:
                object.__setattr__(self, name, _text(value, name, limit=512))
        object.__setattr__(self, "evidence_ids", tuple(_text(item, "evidence_id") for item in self.evidence_ids))
        object.__setattr__(self, "limitations", tuple(_text(item, "limitation") for item in self.limitations))
        if self.privacy_scope != "PRIVATE":
            raise ValueError("personal timeline events are private")


@dataclass(frozen=True)
class PersonalTimeline:
    """A named, owner-scoped timeline envelope for product surfaces."""

    owner_id: str
    events: tuple[TimelineEvent, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "owner_id", _text(self.owner_id, "owner_id"))
        object.__setattr__(self, "events", tuple(self.events))
        if any(event.owner_id != self.owner_id for event in self.events):
            raise ValueError("timeline contains an event from another owner")


class PersonalIntelligenceService:
    """Build misconception continuity and a bounded private timeline.

    Every public operation resolves the supplied session through the
    repository before reading or writing.  The direct SQL reads below are
    fixed statements with bound values and are intentionally owner-filtered.
    """

    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def _owner(self, session_id: str) -> str:
        # The repository's session resolver is the single authorization source.
        return self.repository._principal(session_id)

    def record_misconception(
        self,
        session_id: str,
        *,
        misconception_id: str,
        concept_id: str,
        observed_statement: str,
        correction: str,
        evidence_reference: str,
        detected_at: str,
        related_concept_ids: tuple[str, ...] = (),
        learning_interactions: tuple[str, ...] = (),
    ) -> MisconceptionContinuity:
        owner = self._owner(session_id)
        record = MisconceptionContinuity(
            misconception_id,
            concept_id,
            observed_statement,
            correction,
            evidence_reference,
            detected_at,
            related_concept_ids=related_concept_ids,
            learning_interactions=learning_interactions,
        )
        concept = self.repository.get_node(session_id, concept_id)
        if concept.node_type != "concept":
            raise ValueError("misconception concept_id must reference a concept node")
        for related_id in record.related_concept_ids:
            related = self.repository.get_node(session_id, related_id)
            if related.node_type != "concept":
                raise ValueError("related misconception nodes must be concepts")
        duplicate = self.repository.connection.execute(
            "SELECT 1 FROM p7_misconceptions WHERE misconception_id = ? AND owner_id = ?",
            (record.misconception_id, owner),
        ).fetchone()
        if duplicate is not None:
            raise ValueError("misconception already exists")
        node = PersonalNode(record.misconception_id, "misconception", record.observed_statement, record.to_payload())
        self.repository.save_node(session_id, node)
        self.repository.save_edge(
            session_id,
            PersonalEdge(
                f"{record.misconception_id}:confused-with:{record.concept_id}",
                record.misconception_id,
                record.concept_id,
                "CONFUSED_WITH",
                (record.evidence_reference,),
            ),
        )
        for related_id in record.related_concept_ids:
            self.repository.save_edge(
                session_id,
                PersonalEdge(
                    f"{record.misconception_id}:related-to:{related_id}",
                    record.misconception_id,
                    related_id,
                    "RELATED_TO",
                    (record.evidence_reference,),
                ),
            )
        self.repository.connection.execute(
            "INSERT INTO p7_misconceptions (misconception_id,owner_id,concept_id,observed_statement,correction,evidence_reference,detected_at,corrected_at,status,related_concept_ids,learning_interactions) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                record.misconception_id,
                owner,
                record.concept_id,
                record.observed_statement,
                record.correction,
                record.evidence_reference,
                record.detected_at,
                record.corrected_at,
                record.status,
                json.dumps(list(record.related_concept_ids), sort_keys=True, separators=(",", ":")),
                json.dumps(list(record.learning_interactions), sort_keys=True, separators=(",", ":")),
            ),
        )
        self.repository.connection.commit()
        return record

    def list_misconceptions(self, session_id: str, *, status: str | None = None) -> tuple[MisconceptionContinuity, ...]:
        owner = self._owner(session_id)
        if status is not None and status not in {"OPEN", "CORRECTED"}:
            raise ValueError("misconception status must be OPEN or CORRECTED")
        rows = self.repository.connection.execute(
            "SELECT misconception_id,concept_id,observed_statement,correction,evidence_reference,detected_at,corrected_at,status,related_concept_ids,learning_interactions FROM p7_misconceptions WHERE owner_id = ? ORDER BY misconception_id",
            (owner,),
        ).fetchall()
        if not rows:
            other = self.repository.connection.execute("SELECT 1 FROM p7_misconceptions LIMIT 1").fetchone()
            if other is not None:
                raise PermissionError("misconception records are private to their owner")
        records = tuple(
            MisconceptionContinuity(
                row["misconception_id"],
                row["concept_id"],
                row["observed_statement"],
                row["correction"],
                row["evidence_reference"],
                row["detected_at"],
                row["corrected_at"],
                row["status"],
                tuple(json.loads(row["related_concept_ids"])),
                tuple(json.loads(row["learning_interactions"])),
            )
            for row in rows
        )
        if status is None:
            return records
        return tuple(record for record in records if record.status == status)

    def get_misconception(self, session_id: str, misconception_id: str) -> MisconceptionContinuity:
        node = self.repository.get_node(session_id, misconception_id)
        return MisconceptionContinuity.from_node(node)

    def correct_misconception(
        self,
        session_id: str,
        misconception_id: str,
        *,
        corrected_at: str,
        correction_evidence_id: str,
        evidence_reference: str,
        learning_interaction: str | None = None,
    ) -> MisconceptionContinuity:
        current = self.get_misconception(session_id, misconception_id)
        if current.status == "CORRECTED":
            raise ValueError("misconception is already corrected")
        evidence_id = _text(correction_evidence_id, "correction_evidence_id")
        reference = _text(evidence_reference, "evidence_reference")
        interactions = current.learning_interactions + ((learning_interaction,) if learning_interaction else ())
        corrected = MisconceptionContinuity(
            current.misconception_id,
            current.concept_id,
            current.observed_statement,
            current.correction,
            current.evidence_reference,
            current.detected_at,
            corrected_at,
            "CORRECTED",
            current.related_concept_ids,
            interactions,
        )
        self.repository.save_mastery_evidence(
            session_id,
            MasteryEvidence(
                evidence_id,
                current.concept_id,
                "misconception_correction",
                reference,
                "corrected",
                corrected_at,
                {"misconception_id": current.misconception_id},
            ),
        )
        self.repository.update_node(session_id, misconception_id, corrected.to_payload())
        self.repository.connection.execute(
            "UPDATE p7_misconceptions SET corrected_at = ?, status = 'CORRECTED', learning_interactions = ? WHERE misconception_id = ? AND owner_id = ?",
            (
                corrected.corrected_at,
                json.dumps(list(corrected.learning_interactions), sort_keys=True, separators=(",", ":")),
                misconception_id,
                self._owner(session_id),
            ),
        )
        self.repository.connection.commit()
        return corrected

    def timeline(
        self,
        session_id: str,
        *,
        limit: int = 100,
        since: str | None = None,
        until: str | None = None,
    ) -> tuple[TimelineEvent, ...]:
        owner = self._owner(session_id)
        if since is not None:
            since = _timestamp(since, "since")
        if until is not None:
            until = _timestamp(until, "until")
        if since and until and since > until:
            raise ValueError("since must not be after until")
        bounded = max(1, min(int(limit), 200))
        events: list[TimelineEvent] = []
        history_rows = self.repository.connection.execute(
            "SELECT history_id,source_kind,source_id,source_fingerprint,event_type,title,occurred_at,limitations FROM p7_history_entries WHERE owner_id = ?",
            (owner,),
        ).fetchall()
        for row in history_rows:
            events.append(
                TimelineEvent(
                    f"history:{row['history_id']}",
                    owner,
                    f"history:{row['source_kind']}:{row['event_type']}",
                    row["history_id"],
                    row["title"],
                    row["occurred_at"],
                    row["source_kind"],
                    row["source_id"],
                    row["source_fingerprint"],
                    (),
                    tuple(json.loads(row["limitations"])),
                )
            )
        node_rows = self.repository.connection.execute(
            "SELECT node_id,node_type,title,payload,created_at,updated_at FROM p7_personal_nodes WHERE owner_id = ?",
            (owner,),
        ).fetchall()
        for row in node_rows:
            payload = json.loads(row["payload"])
            refs = payload.get("evidence_ids", ())
            if payload.get("evidence_reference"):
                refs = tuple(refs) + (str(payload["evidence_reference"]),)
            limitations = payload.get("limitations", ())
            events.append(
                TimelineEvent(
                    f"node:{row['node_id']}",
                    owner,
                    f"personal_node:{row['node_type']}",
                    row["node_id"],
                    row["title"],
                    row["updated_at"] or row["created_at"],
                    str(payload.get("source_kind", "")),
                    str(payload.get("source_id", "")),
                    str(payload.get("source_fingerprint", "")),
                    tuple(str(item) for item in refs),
                    tuple(str(item) for item in limitations),
                )
            )
        mastery_rows = self.repository.connection.execute(
            "SELECT evidence_id,concept_id,evidence_reference,outcome,observed_at,details FROM p7_mastery_evidence WHERE owner_id = ?",
            (owner,),
        ).fetchall()
        for row in mastery_rows:
            details = json.loads(row["details"])
            limitations = tuple(str(item) for item in details.get("limitations", ()))
            events.append(
                TimelineEvent(
                    f"mastery:{row['evidence_id']}",
                    owner,
                    f"mastery_evidence:{row['outcome']}",
                    row["evidence_id"],
                    f"Mastery evidence for {row['concept_id']}",
                    row["observed_at"],
                    "mastery_evidence",
                    row["evidence_reference"],
                    "",
                    (row["evidence_id"],),
                    limitations,
                )
            )
        thread_rows = self.repository.connection.execute(
            "SELECT thread_id,title,created_at FROM p7_learning_threads WHERE owner_id = ?",
            (owner,),
        ).fetchall()
        events.extend(
            TimelineEvent(
                f"thread:{row['thread_id']}", owner, "learning_thread", row["thread_id"], row["title"], row["created_at"]
            )
            for row in thread_rows
        )
        filtered = [event for event in events if (since is None or event.occurred_at >= since) and (until is None or event.occurred_at <= until)]
        filtered.sort(key=lambda event: (event.occurred_at, event.event_id))
        return tuple(filtered[:bounded])

    def build_timeline(self, session_id: str, **kwargs: Any) -> tuple[TimelineEvent, ...]:
        return self.timeline(session_id, **kwargs)

    def timeline_snapshot(self, session_id: str, **kwargs: Any) -> PersonalTimeline:
        return PersonalTimeline(self._owner(session_id), self.timeline(session_id, **kwargs))


def record_misconception(repository: Any, session_id: str, **kwargs: Any) -> MisconceptionContinuity:
    return PersonalIntelligenceService(repository).record_misconception(session_id, **kwargs)


def correct_misconception(repository: Any, session_id: str, misconception_id: str, **kwargs: Any) -> MisconceptionContinuity:
    return PersonalIntelligenceService(repository).correct_misconception(session_id, misconception_id, **kwargs)


def build_personal_timeline(repository: Any, session_id: str, **kwargs: Any) -> PersonalTimeline:
    return PersonalIntelligenceService(repository).timeline_snapshot(session_id, **kwargs)


MisconceptionMemory = MisconceptionContinuity
PersonalTimelineService = PersonalIntelligenceService
TimelineService = PersonalIntelligenceService


__all__ = [
    "MisconceptionContinuity",
    "MisconceptionMemory",
    "PersonalIntelligenceService",
    "PersonalTimeline",
    "PersonalTimelineService",
    "TimelineEvent",
    "TimelineService",
    "build_personal_timeline",
    "correct_misconception",
    "record_misconception",
]
