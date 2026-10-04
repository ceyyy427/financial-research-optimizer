from __future__ import annotations

import sqlite3

import pytest

from finahinking.p7 import (
    CommunityComment,
    CommunityPost,
    CommunityRoom,
    PersonalNode,
    Principal,
    SQLiteP7Repository,
    apply_p7_migration,
)
from finahinking.p7.context import EvidenceGroundedGuidance
from finahinking.p7.personal import PersonalIntelligenceService, TimelineEvent
from finahinking.p7.workflows import StrategyJourneyInput, StrategyPersonalCommunityWorkflow


def make_repo() -> SQLiteP7Repository:
    connection = sqlite3.connect(":memory:")
    apply_p7_migration(connection)
    repository = SQLiteP7Repository(connection)
    repository.create_principal(Principal("alice", "Alice"))
    repository.create_principal(Principal("bob", "Bob"))
    repository.create_session("alice-session", "alice")
    repository.create_session("bob-session", "bob")
    return repository


def test_misconception_continuity_records_correction_and_is_private() -> None:
    repository = make_repo()
    service = PersonalIntelligenceService(repository)
    repository.save_node(
        "alice-session",
        PersonalNode("oos", "concept", "Out-of-sample validation", {"definition": "untouched evaluation"}),
    )

    record = service.record_misconception(
        "alice-session",
        misconception_id="mis-oos",
        concept_id="oos",
        observed_statement="A strong backtest guarantees future performance.",
        correction="Out-of-sample evidence can still fail to generalize.",
        evidence_reference="strategy-review-1",
        detected_at="2026-10-03T10:00:00Z",
    )
    assert record.status == "OPEN"
    assert service.list_misconceptions("alice-session")[0].misconception_id == "mis-oos"
    with pytest.raises(PermissionError):
        service.list_misconceptions("bob-session")
    with pytest.raises(PermissionError):
        service.get_misconception("bob-session", "mis-oos")

    corrected = service.correct_misconception(
        "alice-session",
        "mis-oos",
        corrected_at="2026-10-04T10:00:00Z",
        correction_evidence_id="correction-1",
        evidence_reference="strategy-review-2",
    )
    assert corrected.status == "CORRECTED"
    assert corrected.corrected_at == "2026-10-04T10:00:00Z"
    assert repository.get_mastery_state("alice-session", "oos").state != "NEEDS_REVIEW"


def test_timeline_is_owner_scoped_bounded_and_provenance_preserving() -> None:
    repository = make_repo()
    service = PersonalIntelligenceService(repository)
    repository.save_node("alice-session", PersonalNode("c", "concept", "Momentum", {"definition": "ranked return"}))
    repository.save_history_entry(
        "alice-session",
        history_id="h-alice",
        source_kind="strategy",
        source_id="s1",
        source_fingerprint="a" * 64,
        event_type="completed",
        title="Momentum test",
        occurred_at="2026-10-03T11:00:00Z",
        limitations=["historical only"],
    )
    repository.save_node("bob-session", PersonalNode("bob-c", "concept", "Private", {"secret": True}))
    events = service.timeline("alice-session", limit=10)
    assert events
    assert all(isinstance(event, TimelineEvent) for event in events)
    assert all(event.owner_id == "alice" for event in events)
    assert any(event.source_id == "s1" and "historical only" in event.limitations for event in events)
    assert "bob-c" not in {event.object_id for event in events}
    assert len(service.timeline("alice-session", limit=1)) == 1


def test_guidance_is_evidence_grounded_optional_and_truth_preserving() -> None:
    repository = make_repo()
    service = PersonalIntelligenceService(repository)
    repository.save_node("alice-session", PersonalNode("oos", "concept", "OOS validation", {"definition": "untouched"}))
    service.record_misconception(
        "alice-session",
        misconception_id="m1",
        concept_id="oos",
        observed_statement="Backtest success proves future success.",
        correction="Use untouched data to evaluate generalization.",
        evidence_reference="e-m1",
        detected_at="2026-10-03T10:00:00Z",
    )
    result = EvidenceGroundedGuidance(repository).suggest("alice-session", purpose="review a backtest")
    assert result.truth_preserved is True
    assert result.evidence_ids == ("e-m1",)
    assert result.suggestions
    assert "review" in result.suggestions[0].text.lower()
    assert result.context_node_ids == ("m1", "oos") or set(result.context_node_ids) == {"m1", "oos"}


def test_strategy_journey_stays_private_until_explicit_projection_and_supports_question_loop() -> None:
    repository = make_repo()
    workflow = StrategyPersonalCommunityWorkflow(repository)
    repository.create_room("alice-session", CommunityRoom("room", "Research", "Evidence only"))
    repository.join_room("bob-session", "room")
    result = workflow.run(
        StrategyJourneyInput(
            session_id="alice-session",
            strategy_id="strategy-1",
            strategy_fingerprint="f" * 64,
            title="Momentum strategy",
            payload={"summary": "historical result", "limitations": ["not a forecast"]},
            concept_ids=("oos",),
            projection_fields=("summary", "limitations"),
            room_id="room",
            publish=True,
            consent=True,
            projection_id="projection-journey",
            post=CommunityPost("post-journey", "room", "alice", "QUANT_FINDING", "Result", "Historical only."),
        ),
        create_missing_concepts=True,
    )
    assert result.strategy_node.node_type == "strategy"
    assert result.history_id == "history-strategy-1"
    assert result.projection is not None
    assert result.post_id == "post-journey"
    repository.add_comment("bob-session", CommunityComment("counter", "post-journey", "bob", "Counter-evidence is needed."))
    question = workflow.save_discussion_as_question("alice-session", "post-journey", "question-1", "What would change this result?")
    assert question.node_type == "question"
    assert repository.get_public_projection("projection-journey", "bob-session").projection_id == "projection-journey"
