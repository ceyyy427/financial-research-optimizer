"""Deterministic P7 personal-to-community strategy journey.

The workflow is deliberately a composition of existing P6.6 artifacts and
the P7 repository.  It records references and learning evidence; it does not
recompute a strategy, rank investments, or execute a broker action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .context import EvidenceGroundedGuidance, GuidanceResult
from .models import (
    CommunityPost,
    LearningThread,
    MasteryEvidence,
    PersonalNode,
    ProjectionSpec,
    PublicProjection,
)
from .personal import MisconceptionContinuity, PersonalIntelligenceService

if TYPE_CHECKING:
    from finahinking.p6_6.lab import LabRun


def _text(value: Any, label: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    value = value.strip()
    if len(value) > limit:
        raise ValueError(f"{label} is too long")
    return value


@dataclass(frozen=True)
class StrategyJourneyInput:
    session_id: str
    strategy_id: str
    strategy_fingerprint: str
    title: str
    payload: dict[str, Any]
    concept_ids: tuple[str, ...] = ()
    strategy_limitations: tuple[str, ...] = ()
    occurred_at: str = "1970-01-01T00:00:00Z"
    feature_fingerprint: str | None = None
    backtest_fingerprint: str | None = None
    oos_fingerprint: str | None = None
    paper_fingerprint: str | None = None
    projection_fields: tuple[str, ...] = ()
    projection_id: str | None = None
    projection_visibility: str = "SHARED_ROOM"
    room_id: str | None = None
    post: CommunityPost | None = None
    publish: bool = False
    consent: bool = False
    code_commit: str | None = None
    misconception_id: str | None = None
    misconception_observed: str | None = None
    misconception_correction: str | None = None
    misconception_evidence_reference: str | None = None
    detected_at: str | None = None
    create_missing_concepts: bool = False

    def __post_init__(self) -> None:
        for name in ("session_id", "strategy_id", "strategy_fingerprint", "title"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        if not isinstance(self.payload, dict):
            raise TypeError("strategy payload must be a JSON object")
        if not isinstance(self.create_missing_concepts, bool):
            raise TypeError("create_missing_concepts must be boolean")
        object.__setattr__(self, "concept_ids", tuple(_text(item, "concept_id") for item in self.concept_ids))
        object.__setattr__(self, "strategy_limitations", tuple(_text(item, "limitation") for item in self.strategy_limitations))
        object.__setattr__(self, "occurred_at", _text(self.occurred_at, "occurred_at", 80))
        for name in ("feature_fingerprint", "backtest_fingerprint", "oos_fingerprint", "paper_fingerprint", "code_commit"):
            value = getattr(self, name, None)
            if value is not None:
                object.__setattr__(self, name, _text(value, name, 512))
        object.__setattr__(self, "projection_fields", tuple(_text(item, "projection_field") for item in self.projection_fields))
        if self.projection_visibility not in {"PRIVATE", "SHARED_ROOM", "SHARED_GROUP", "PUBLIC"}:
            raise ValueError("projection visibility is invalid")
        if self.publish:
            if not self.projection_id:
                raise ValueError("projection_id is required when publish=True")
            if not self.projection_fields:
                raise ValueError("projection_fields are required when publish=True")
            if not self.consent:
                raise ValueError("explicit consent is required when publish=True")
            if self.projection_visibility == "SHARED_ROOM" and not self.room_id:
                raise ValueError("room_id is required for a room projection")
        if self.post is not None and not self.room_id:
            raise ValueError("room_id is required when a community post is supplied")
        misconception_values = (self.misconception_id, self.misconception_observed, self.misconception_correction, self.misconception_evidence_reference, self.detected_at)
        if any(value is not None for value in misconception_values) and not all(value is not None for value in misconception_values):
            raise ValueError("misconception fields must be supplied together")

    @classmethod
    def from_lab_run(
        cls,
        session_id: str,
        lab_run: LabRun,
        *,
        concept_ids: tuple[str, ...] = (),
        payload: dict[str, Any] | None = None,
        create_missing_concepts: bool = False,
        code_commit: str | None = None,
        **journey_fields: Any,
    ) -> StrategyJourneyInput:
        """Adapt one real P6.6 ``StrategyResearchLab`` result without recomputation."""

        spec = getattr(lab_run, "spec", None)
        ir = getattr(lab_run, "ir", None)
        historical = getattr(lab_run, "historical", None) or {}
        if spec is None or ir is None or not isinstance(historical, dict):
            raise TypeError("lab_run must expose spec, ir and historical")
        backtest = historical.get("backtest")
        if backtest is None:
            backtest = getattr(historical.get("experiment"), "backtest", None)
        backtest_fingerprint = getattr(backtest, "fingerprint", None)
        paper = getattr(lab_run, "paper", None)
        paper_fingerprint = getattr(paper, "fingerprint", None)
        oos = getattr(lab_run, "oos", None)
        if oos is None:
            for key in ("oos", "oos_run", "oos_report", "walk_forward"):
                if historical.get(key) is not None:
                    oos = historical[key]
                    break
        oos_fingerprint = getattr(oos, "fingerprint", None) or getattr(lab_run, "oos_fingerprint", None)
        quant_run = historical.get("quant_run") or getattr(historical.get("experiment"), "quant_run", None)
        parameters = getattr(quant_run, "parameters", {}) or {}
        resolved_code_commit = code_commit or (parameters.get("code_commit") if isinstance(parameters, dict) else None)
        limitations: list[str] = list(getattr(spec, "limitations", ()))
        for value in (
            getattr(historical.get("evaluation"), "limitations", ()),
            getattr(backtest, "limitations", ()),
            getattr(paper, "limitations", ()),
            getattr(historical.get("experiment"), "limitations", ()),
        ):
            limitations.extend(str(item) for item in (value or ()))
        resolved_limitations = tuple(dict.fromkeys(str(item) for item in limitations))
        result_payload = {
            "summary": "Historical P6.6 strategy evidence; not a forecast.",
            "strategy_id": spec.strategy_id,
            "strategy_version": spec.version,
            "feature_graph_fingerprint": ir.feature_graph_fingerprint,
            "backtest_fingerprint": backtest_fingerprint,
            "oos_fingerprint": oos_fingerprint,
            "paper_fingerprint": paper_fingerprint,
            "limitations": list(resolved_limitations),
            "provenance": {
                "code_commit": resolved_code_commit,
                "strategy_fingerprint": spec.fingerprint,
                "feature_graph_fingerprint": ir.feature_graph_fingerprint,
                "backtest_fingerprint": backtest_fingerprint,
                "oos_fingerprint": oos_fingerprint,
                "paper_fingerprint": paper_fingerprint,
            },
        }
        if payload:
            result_payload.update(payload)
        result_payload["limitations"] = list(resolved_limitations)
        journey_fields.setdefault("projection_fields", ("summary", "limitations", "provenance"))
        journey_fields.setdefault("occurred_at", getattr(paper, "started_at", "1970-01-01T00:00:00Z"))
        journey_fields.setdefault("strategy_limitations", resolved_limitations)
        journey_fields.setdefault("feature_fingerprint", ir.feature_graph_fingerprint)
        journey_fields.setdefault("backtest_fingerprint", backtest_fingerprint)
        journey_fields.setdefault("oos_fingerprint", oos_fingerprint)
        journey_fields.setdefault("paper_fingerprint", paper_fingerprint)
        journey_fields.setdefault("code_commit", resolved_code_commit)
        return cls(
            session_id=session_id,
            strategy_id=spec.strategy_id,
            strategy_fingerprint=spec.fingerprint,
            title=spec.name,
            payload=result_payload,
            concept_ids=concept_ids,
            create_missing_concepts=create_missing_concepts,
            **journey_fields,
        )


@dataclass(frozen=True)
class StrategyJourneyResult:
    strategy_node: PersonalNode
    history_id: str
    mastery_evidence_ids: tuple[str, ...]
    learning_thread_id: str
    guidance: GuidanceResult
    misconception: MisconceptionContinuity | None = None
    projection: PublicProjection | None = None
    post_id: str | None = None
    question_node: PersonalNode | None = None


class StrategyPersonalCommunityWorkflow:
    """Run a private strategy continuity journey with opt-in projection."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self.personal = PersonalIntelligenceService(repository)
        self.guidance = EvidenceGroundedGuidance(repository)

    def run(self, journey: StrategyJourneyInput, *, create_missing_concepts: bool = False) -> StrategyJourneyResult:
        if not isinstance(journey, StrategyJourneyInput):
            raise TypeError("journey must be StrategyJourneyInput")
        create_missing_concepts = create_missing_concepts or journey.create_missing_concepts
        self.repository._principal(journey.session_id)
        if journey.misconception_id is not None and not journey.concept_ids:
            raise ValueError("a misconception requires at least one concept_id")
        existing_concepts: dict[str, PersonalNode] = {}
        for concept_id in journey.concept_ids:
            try:
                concept = self.repository.get_node(journey.session_id, concept_id)
            except KeyError:
                if not create_missing_concepts:
                    raise
                continue
            if concept.node_type != "concept":
                raise ValueError(f"{concept_id} is not a concept node")
            existing_concepts[concept_id] = concept
        payload_limitations = journey.payload.get("limitations", ())
        if not isinstance(payload_limitations, (list, tuple)):
            raise TypeError("strategy payload limitations must be a sequence")
        limitations = journey.strategy_limitations or tuple(_text(item, "limitation") for item in payload_limitations)
        strategy_payload = dict(journey.payload)
        strategy_payload.update(
            {
                "source_kind": "strategy",
                "source_id": journey.strategy_id,
                "source_fingerprint": journey.strategy_fingerprint,
                "strategy_fingerprint": journey.strategy_fingerprint,
                "limitations": list(limitations),
            }
        )
        strategy_node = PersonalNode(journey.strategy_id, "strategy", journey.title, strategy_payload)
        self.repository.save_node(journey.session_id, strategy_node)
        history_id = f"history-{journey.strategy_id}"
        self.repository.save_history_entry(
            journey.session_id,
            history_id=history_id,
            source_kind="strategy",
            source_id=journey.strategy_id,
            source_fingerprint=journey.strategy_fingerprint,
            event_type="completed",
            title=journey.title,
            occurred_at=journey.occurred_at,
            limitations=limitations,
        )
        self.repository.link_artifact(
            journey.session_id,
            "strategy",
            journey.strategy_id,
            journey.strategy_fingerprint,
            journey.projection_fields or tuple(strategy_payload),
            code_commit=journey.code_commit,
        )
        self.repository.save_strategy_version(
            journey.session_id,
            strategy_version_id=f"version-{journey.strategy_id}",
            strategy_id=journey.strategy_id,
            strategy_fingerprint=journey.strategy_fingerprint,
            feature_fingerprint=journey.feature_fingerprint,
            backtest_fingerprint=journey.backtest_fingerprint,
            oos_fingerprint=journey.oos_fingerprint,
            paper_fingerprint=journey.paper_fingerprint,
            limitations=limitations,
            code_commit=journey.code_commit,
        )
        concept_nodes: list[str] = []
        mastery_ids: list[str] = []
        for concept_id in journey.concept_ids:
            concept = existing_concepts.get(concept_id)
            if concept is None:
                concept = PersonalNode(concept_id, "concept", concept_id, {"source_kind": "strategy", "source_id": journey.strategy_id})
                self.repository.save_node(journey.session_id, concept)
            concept_nodes.append(concept.node_id)
            evidence_id = f"mastery-{journey.strategy_id}-{concept_id}"
            self.repository.save_mastery_evidence(
                journey.session_id,
                MasteryEvidence(
                    evidence_id,
                    concept.node_id,
                    "strategy_use",
                    journey.strategy_id,
                    "neutral",
                    journey.occurred_at,
                    {"strategy_fingerprint": journey.strategy_fingerprint, "limitations": list(limitations)},
                ),
            )
            mastery_ids.append(evidence_id)

        misconception: MisconceptionContinuity | None = None
        if journey.misconception_id is not None:
            misconception = self.personal.record_misconception(
                journey.session_id,
                misconception_id=journey.misconception_id,
                concept_id=journey.concept_ids[0] if journey.concept_ids else journey.strategy_id,
                observed_statement=journey.misconception_observed or "",
                correction=journey.misconception_correction or "",
                evidence_reference=journey.misconception_evidence_reference or "",
                detected_at=journey.detected_at or "1970-01-01T00:00:00Z",
            )
            concept_nodes.append(misconception.misconception_id)

        thread_nodes = tuple(dict.fromkeys((*concept_nodes, journey.strategy_id)))
        thread_id = f"thread-{journey.strategy_id}"
        self.repository.create_learning_thread(journey.session_id, LearningThread(thread_id, journey.title, thread_nodes))
        guidance = self.guidance.suggest(journey.session_id, purpose=f"review strategy {journey.strategy_id}")

        projection: PublicProjection | None = None
        post_id: str | None = None
        if journey.publish:
            assert journey.projection_id is not None
            projection = self.repository.publish_projection(
                journey.session_id,
                ProjectionSpec(
                    journey.projection_id,
                    "strategy",
                    journey.strategy_id,
                    journey.strategy_fingerprint,
                    journey.projection_fields,
                    journey.projection_visibility,
                    limitations=limitations,
                    room_id=journey.room_id,
                ),
                strategy_payload,
                consent=journey.consent,
            )
            if journey.post is not None:
                self.repository.create_post(journey.session_id, journey.post)
                self.repository.attach_projection(journey.session_id, journey.post.post_id, projection.projection_id, "strategy")
                post_id = journey.post.post_id

        return StrategyJourneyResult(strategy_node, history_id, tuple(mastery_ids), thread_id, guidance, misconception, projection, post_id)

    def save_discussion_as_question(self, session_id: str, post_id: str, node_id: str, title: str) -> PersonalNode:
        return self.repository.save_as_question(session_id, post_id, node_id, title)

    def add_counter_evidence(self, session_id: str, comment: Any) -> None:
        self.repository.add_comment(session_id, comment)


def run_strategy_personal_community_journey(
    repository: Any,
    journey: StrategyJourneyInput | None = None,
    *,
    create_missing_concepts: bool = False,
    **journey_fields: Any,
) -> StrategyJourneyResult:
    """Convenient function form; keyword fields build the typed input.

    Keeping the input dataclass as the canonical contract prevents accidental
    omission of consent and provenance, while this form is useful to a small
    CLI or notebook vertical slice.
    """

    if journey is None:
        journey = StrategyJourneyInput(**journey_fields)
    elif journey_fields:
        raise TypeError("journey fields cannot accompany a StrategyJourneyInput")
    return StrategyPersonalCommunityWorkflow(repository).run(journey, create_missing_concepts=create_missing_concepts)


StrategyJourney = StrategyPersonalCommunityWorkflow


__all__ = [
    "StrategyJourney",
    "StrategyJourneyInput",
    "StrategyJourneyResult",
    "StrategyPersonalCommunityWorkflow",
    "run_strategy_personal_community_journey",
]
