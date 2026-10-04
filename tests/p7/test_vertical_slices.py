from __future__ import annotations

import sqlite3

import pytest

from finahinking.p7 import (
    CommunityPost,
    CommunityRoom,
    LearningThread,
    MasteryEvidence,
    PersonalEdge,
    PersonalNode,
    Principal,
    ProjectionSpec,
    SQLiteP7Repository,
    apply_p7_migration,
)


def make_repo() -> SQLiteP7Repository:
    connection = sqlite3.connect(":memory:")
    apply_p7_migration(connection)
    return SQLiteP7Repository(connection)


def test_private_continuity_slice_is_owner_scoped_and_exportable() -> None:
    repository = make_repo()
    repository.create_principal(Principal("alice", "Alice"))
    repository.create_session("alice-session", "alice")
    concept = PersonalNode("c1", "concept", "Point in time", {"definition": "available_at"})
    note = PersonalNode("n1", "note", "Review", {"body": "check revisions"})
    repository.save_node("alice-session", concept)
    repository.save_node("alice-session", note)
    repository.save_edge("alice-session", PersonalEdge("e1", "n1", "c1", "QUESTIONED"))
    repository.save_mastery_evidence("alice-session", MasteryEvidence("m1", "c1", "explanation", "card:c1", "correct", "2026-10-03T00:00:00Z"))
    repository.create_learning_thread("alice-session", LearningThread("t1", "Temporal review", ("n1", "c1")))
    repository.save_history_entry("alice-session", history_id="h1", source_kind="research_run", source_id="r1", source_fingerprint="a" * 64, event_type="completed", title="Revision review", occurred_at="2026-10-03T00:00:00Z", limitations=["fixture"])
    repository.save_object("alice-session", saved_id="saved-claim", source_kind="claim", source_id="claim-1", source_fingerprint="a" * 64, note="revisit this claim")

    context = repository.authorized_context("alice-session", purpose="review", limit=1)
    exported = repository.export_personal("alice-session")
    assert len(context) == 1
    assert exported["principal_id"] == "alice"
    assert exported["mastery"][0]["evidence_ids"] == ["m1"]
    assert exported["edges"][0]["relation_type"] == "QUESTIONED"
    assert exported["saved_objects"][0]["saved_id"] == "saved-claim"

    repository.delete_personal("alice-session")
    with pytest.raises(KeyError):
        repository.get_node("alice-session", "c1")
    assert repository.export_personal("alice-session")["nodes"] == []
    assert repository.export_personal("alice-session")["learning_threads"] == []
    assert repository.export_personal("alice-session")["saved_objects"] == []


def test_projection_to_community_slice_marks_stale_and_requires_membership() -> None:
    repository = make_repo()
    repository.create_principal(Principal("alice", "Alice"))
    repository.create_principal(Principal("bob", "Bob"))
    repository.create_session("alice-session", "alice")
    repository.create_session("bob-session", "bob")
    repository.create_room("alice-session", CommunityRoom("r1", "Evidence", "Evidence room"))
    repository.join_room("bob-session", "r1")
    repository.link_artifact("alice-session", "research_run", "run1", "a" * 64, ("summary",))
    repository.publish_projection("alice-session", ProjectionSpec("p1", "research_run", "run1", "a" * 64, ("summary",), "SHARED_ROOM", room_id="r1"), {"summary": "historical"}, consent=True)
    repository.create_post("bob-session", CommunityPost("post1", "r1", "bob", "QUANT_FINDING", "Result", "Historical only."))
    repository.attach_projection("bob-session", "post1", "p1", "research")
    repository.link_artifact("alice-session", "research_run", "run1", "b" * 64, ("summary",))
    assert repository.refresh_stale_projections("alice-session") == 1
    with pytest.raises(PermissionError):
        repository.get_public_projection("p1", "bob-session")
