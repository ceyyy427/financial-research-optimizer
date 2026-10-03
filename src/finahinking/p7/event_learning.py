"""Adapter for the P6.5 real-event -> P7 personal-learning slice.

The adapter consumes already-admitted P6.5 records.  It does not fetch a
provider, reinterpret an observation, or turn a macro event into advice.  It
creates owner-scoped P7 nodes/edges, records an evidence-derived mastery
interaction, and appends a source-fingerprinted history entry.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from finahinking.p6_5.models import Concept, Event, Evidence

from .models import MasteryEvidence, PersonalEdge, PersonalNode, ProjectionSpec, PublicProjection
from .repository import SQLiteP7Repository


@dataclass(frozen=True)
class EventLearningSlice:
    """Identifiers created by one deterministic event-learning ingestion."""

    event_id: str
    event_node_id: str
    evidence_node_ids: tuple[str, ...]
    concept_node_ids: tuple[str, ...]
    mastery_evidence_ids: tuple[str, ...]
    history_id: str


class EventLearningAdapter:
    """Build private continuity from a validated P6.5 event."""

    def __init__(self, repository: SQLiteP7Repository) -> None:
        if not isinstance(repository, SQLiteP7Repository):
            raise TypeError("repository must be a SQLiteP7Repository")
        self.repository = repository

    @staticmethod
    def _event_node(event: Event) -> PersonalNode:
        return PersonalNode(
            f"event:{event.event_id}",
            "event",
            f"{event.event_type}: {event.reference_period}",
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "source_id": event.source_id,
                "reference_period": event.reference_period,
                "published_at": event.published_at,
                "available_at": event.available_at,
                "observation_ids": list(event.observation_ids),
                "evidence_ids": list(event.evidence_ids),
                "revision_status": event.revision_status.value,
                "source_fingerprint": event.fingerprint,
            },
        )

    @staticmethod
    def _evidence_node(evidence: Evidence) -> PersonalNode:
        return PersonalNode(
            f"evidence:{evidence.evidence_id}",
            "evidence",
            evidence.reference,
            {
                "evidence_id": evidence.evidence_id,
                "evidence_type": evidence.evidence_type,
                "source_id": evidence.source_id,
                "capture_id": evidence.capture_id,
                "reference": evidence.reference,
                "status": evidence.status.value,
                "scope": evidence.scope,
                "limitations": list(evidence.limitations),
                "source_fingerprint": evidence.source_fingerprint,
                "evidence_fingerprint": evidence.fingerprint,
            },
        )

    @staticmethod
    def _concept_node(concept: Concept) -> PersonalNode:
        return PersonalNode(
            f"concept:{concept.concept_id}",
            "concept",
            concept.name,
            {
                "concept_id": concept.concept_id,
                "definition": concept.definition,
                "formula": concept.formula,
                "evidence_ids": list(concept.evidence_ids),
                "source": "p6_5_concept",
            },
        )

    def ingest(
        self,
        session_id: str,
        event: Event,
        *,
        evidence: Sequence[Evidence],
        concepts: Sequence[Concept],
        mastery_outcomes: Mapping[str, str],
        observed_at: str | None = None,
    ) -> EventLearningSlice:
        """Persist a complete event-learning slice under one user session.

        Every event evidence ID must be supplied as an admitted P6.5
        ``Evidence`` record, every concept must cite event evidence, and each
        concept must receive an explicit mastery outcome.  Missing pieces fail
        closed instead of inventing a personal learning signal.
        """

        if not isinstance(event, Event):
            raise TypeError("event must be a P6.5 Event")
        evidence_items = tuple(evidence)
        evidence_by_id = {item.evidence_id: item for item in evidence_items}
        if len(evidence_by_id) != len(evidence_items):
            raise ValueError("evidence ids must be unique")
        missing_event_evidence = set(event.evidence_ids) - set(evidence_by_id)
        if missing_event_evidence:
            raise ValueError(f"event evidence is incomplete: {sorted(missing_event_evidence)}")
        concept_items = tuple(concepts)
        concept_by_id = {item.concept_id: item for item in concept_items}
        if len(concept_by_id) != len(concept_items):
            raise ValueError("concept ids must be unique")
        if not concept_by_id:
            raise ValueError("event-learning slice requires at least one concept")
        if set(mastery_outcomes) != set(concept_by_id):
            raise ValueError("each concept requires one explicit mastery outcome")
        for concept in concept_items:
            if not concept.evidence_ids:
                raise ValueError("concept must cite event evidence")
            if not set(concept.evidence_ids).issubset(event.evidence_ids):
                raise ValueError("concept evidence must belong to the event")
            if not set(concept.evidence_ids).issubset(evidence_by_id):
                raise ValueError("concept evidence records are incomplete")
            if mastery_outcomes[concept.concept_id] not in {"correct", "incorrect", "neutral", "corrected"}:
                raise ValueError("mastery outcome is invalid")

        event_node = self._event_node(event)
        self.repository.save_node(session_id, event_node)
        evidence_nodes = tuple(self._evidence_node(item) for item in evidence if item.evidence_id in event.evidence_ids)
        for node in evidence_nodes:
            self.repository.save_node(session_id, node)
            self.repository.save_edge(session_id, PersonalEdge(f"edge:{event.event_id}:{node.node_id}", event_node.node_id, node.node_id, "SUPPORTED_BY"))

        concept_nodes = tuple(self._concept_node(item) for item in concept_items)
        for node, concept in zip(concept_nodes, concept_items):
            self.repository.save_node(session_id, node)
            self.repository.save_edge(session_id, PersonalEdge(f"edge:{event.event_id}:{node.node_id}", node.node_id, event_node.node_id, "DERIVED_FROM"))

        mastery_ids: list[str] = []
        for concept in concept_items:
            mastery_id = f"mastery:{event.event_id}:{concept.concept_id}"
            mastery_ids.append(mastery_id)
            self.repository.save_mastery_evidence(
                session_id,
                MasteryEvidence(
                    mastery_id,
                    f"concept:{concept.concept_id}",
                    "research_use",
                    f"event:{event.event_id}",
                    mastery_outcomes[concept.concept_id],
                    observed_at or event.available_at or event.published_at,
                    {"event_id": event.event_id, "evidence_ids": list(concept.evidence_ids)},
                ),
            )

        limitations = sorted({limitation for item in evidence_by_id.values() for limitation in item.limitations})
        history_id = f"history:event:{event.event_id}"
        self.repository.save_history_entry(
            session_id,
            history_id=history_id,
            source_kind="p6_5_event",
            source_id=event.event_id,
            source_fingerprint=event.fingerprint,
            event_type="understood",
            title=f"{event.event_type}: {event.reference_period}",
            occurred_at=observed_at or event.available_at or event.published_at,
            limitations=limitations or ["Event interpretation remains bounded by admitted source evidence."],
        )
        self.repository.link_artifact(
            session_id,
            "p6_5_event",
            event.event_id,
            event.fingerprint,
            ("event_type", "reference_period", "published_at", "revision_status", "limitations"),
        )
        return EventLearningSlice(event.event_id, event_node.node_id, tuple(node.node_id for node in evidence_nodes), tuple(node.node_id for node in concept_nodes), tuple(mastery_ids), history_id)

    def ingest_journey(
        self,
        session_id: str,
        journey: object,
        *,
        mastery_outcomes: Mapping[str, str] | None = None,
        projection_id: str | None = None,
        visibility: str = "PRIVATE",
        consent: bool = False,
        room_id: str | None = None,
    ) -> EventLearningSlice:
        """Bridge a real P6.5 ``ProductJourney`` into private P7 continuity.

        ``UnderstandingEngine.run_cpi_journey`` is the authority for source
        admission, claims, evidence, and the event.  This method only stores
        those already-admitted records as owner-scoped P7 nodes and a
        fingerprinted timeline entry.  The journey's ``user_id`` must be the
        authenticated session principal; a caller cannot import another
        person's event into their graph.
        """

        from finahinking.p6_5.product import ProductJourney

        if not isinstance(journey, ProductJourney):
            raise TypeError("journey must be a P6.5 ProductJourney")
        owner = self.repository._principal(session_id)
        if owner != journey.user_id:
            raise PermissionError("journey user does not match authenticated principal")
        evidence_items = tuple(journey.evidence)
        evidence_by_id = {item.evidence_id: item for item in evidence_items}
        if len(evidence_by_id) != len(evidence_items):
            raise ValueError("journey evidence ids must be unique")
        for claim in journey.claims:
            missing = set(claim.evidence_ids) - set(evidence_by_id)
            if missing:
                raise ValueError(f"journey claim evidence is incomplete: {sorted(missing)}")
        event_evidence = tuple(evidence_by_id[item] for item in journey.event.evidence_ids)
        concepts = tuple(journey.knowledge_bridge.concepts)
        outcomes = dict(mastery_outcomes or {concept.concept_id: "neutral" for concept in concepts})
        slice_result = self.ingest(
            session_id,
            journey.event,
            evidence=event_evidence,
            concepts=concepts,
            mastery_outcomes=outcomes,
            observed_at=journey.event.available_at or journey.event.published_at,
        )

        # The quant result and other journey-level evidence are not part of
        # Event.evidence_ids, but they remain valid, source-bound evidence and
        # must not disappear when the journey enters personal continuity.
        known_nodes = set(slice_result.evidence_node_ids)
        event_node_id = slice_result.event_node_id
        for item in evidence_items:
            node = self._evidence_node(item)
            if node.node_id in known_nodes:
                continue
            self.repository.save_node(session_id, node)
            self.repository.save_edge(
                session_id,
                PersonalEdge(f"edge:{journey.event.event_id}:{node.node_id}", event_node_id, node.node_id, "SUPPORTED_BY"),
            )

        # Claims remain typed records, not silently upgraded to truth by being
        # in a personal graph.  Their evidence IDs and limitations are kept
        # verbatim for later review or an explicit projection.
        for claim in journey.claims:
            claim_node = PersonalNode(
                f"claim:{claim.claim_id}",
                "claim",
                claim.text,
                {
                    "claim_id": claim.claim_id,
                    "claim_type": claim.claim_type.value,
                    "evidence_ids": list(claim.evidence_ids),
                    "evidence_status": claim.evidence_status.value,
                    "source_fingerprint": claim.source_fingerprint,
                    "source_verified": claim.source_verified,
                    "limitations": list(claim.limitations),
                },
            )
            self.repository.save_node(session_id, claim_node)
            for evidence_id in claim.evidence_ids:
                evidence_node_id = f"evidence:{evidence_id}"
                if evidence_id in evidence_by_id:
                    self.repository.save_edge(
                        session_id,
                        PersonalEdge(f"edge:{claim.claim_id}:{evidence_id}", claim_node.node_id, evidence_node_id, "SUPPORTED_BY"),
                    )

        if projection_id is not None:
            self.publish_projection(
                session_id,
                journey.event,
                projection_id=projection_id,
                visibility=visibility,
                consent=consent,
                room_id=room_id,
                limitations=(
                    "P6.5 journey projection is descriptive and source-bound; it is not a forecast.",
                    journey.learning_card.limitation,
                ),
            )
        return slice_result

    def publish_projection(
        self,
        session_id: str,
        event: Event,
        *,
        projection_id: str,
        visibility: str,
        consent: bool,
        limitations: Sequence[str] = (),
        room_id: str | None = None,
    ) -> PublicProjection:
        """Publish only the allow-listed, non-private event summary."""

        payload = {
            "event_type": event.event_type,
            "reference_period": event.reference_period,
            "published_at": event.published_at,
            "revision_status": event.revision_status.value,
            "limitations": list(limitations),
        }
        spec = ProjectionSpec(
            projection_id,
            "p6_5_event",
            event.event_id,
            event.fingerprint,
            tuple(payload),
            visibility,
            limitations=tuple(limitations) or ("Projection is descriptive and source-bound; it is not a forecast.",),
            room_id=room_id,
        )
        return self.repository.publish_projection(session_id, spec, payload, consent=consent)


__all__ = ["EventLearningAdapter", "EventLearningSlice"]
