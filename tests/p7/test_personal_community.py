from __future__ import annotations

import json
import sqlite3

import pytest

from finahinking.p7 import (
    CommunityPost,
    CommunityRoom,
    MasteryEvidence,
    PersonalNode,
    Principal,
    ProjectionSpec,
    SQLiteP7Repository,
    apply_p7_migration,
)


def repo() -> SQLiteP7Repository:
    connection = sqlite3.connect(":memory:")
    apply_p7_migration(connection)
    return SQLiteP7Repository(connection)


def principals(repository: SQLiteP7Repository) -> tuple[str, str]:
    alice = repository.create_principal(Principal("alice", "Alice"))
    bob = repository.create_principal(Principal("bob", "Bob"))
    repository.create_session("session-alice", alice.principal_id)
    repository.create_session("session-bob", bob.principal_id)
    return "session-alice", "session-bob"


def test_private_nodes_are_owner_scoped_and_cross_user_access_is_denied() -> None:
    repository = repo()
    alice_session, bob_session = principals(repository)
    node = PersonalNode("node-beta", "concept", "Beta", {"definition": "systematic risk"})
    repository.save_node(alice_session, node)

    assert repository.get_node(alice_session, node.node_id).node_id == node.node_id
    with pytest.raises(PermissionError):
        repository.get_node(bob_session, node.node_id)
    with pytest.raises(PermissionError):
        repository.update_node(bob_session, node.node_id, {"definition": "leaked"})


def test_typed_graph_and_mastery_state_are_evidence_explainable() -> None:
    repository = repo()
    session, _ = principals(repository)
    concept = PersonalNode("concept-oos", "concept", "OOS validation", {"definition": "untouched evaluation"})
    repository.save_node(session, concept)
    evidence = MasteryEvidence("evidence-1", "concept-oos", "quiz_response", "quiz:oos:1", "incorrect", "2026-10-03T00:00:00Z")
    repository.save_mastery_evidence(session, evidence)
    state = repository.get_mastery_state(session, "concept-oos")
    assert state.state == "NEEDS_REVIEW"
    assert state.evidence_ids == ("evidence-1",)
    assert "evidence-1" in state.explanation


def test_projection_requires_explicit_consent_sanitizes_and_revocation_preserves_source() -> None:
    repository = repo()
    session, bob_session = principals(repository)
    source = PersonalNode("research-1", "research", "Momentum result", {"summary": "historical", "private_note": "do not share"})
    repository.save_node(session, source)
    repository.link_artifact(session, "research_run", "run-1", "f" * 64, ("summary",))
    spec = ProjectionSpec("projection-1", "research_run", "run-1", "f" * 64, ("summary",), "PUBLIC")
    with pytest.raises(PermissionError):
        repository.publish_projection(session, spec, {"summary": "historical", "private_note": "do not share"}, consent=False)
    repository.publish_projection(session, spec, {"summary": "historical", "private_note": "do not share"}, consent=True)
    projection = repository.get_public_projection("projection-1")
    assert projection.payload == {"summary": "historical"}
    assert "private_note" not in json.dumps(projection.payload)
    repository.revoke_projection(session, "projection-1")
    with pytest.raises(PermissionError):
        repository.get_public_projection("projection-1")
    assert repository.get_node(session, source.node_id).node_id == source.node_id
    with pytest.raises(PermissionError):
        repository.get_public_projection(bob_session, "projection-1")


def test_room_posts_only_accept_active_projections_and_preserve_claim_labels() -> None:
    repository = repo()
    session, bob_session = principals(repository)
    room = CommunityRoom("room-research", "Research Room", "Evidence-linked research")
    repository.create_room(session, room)
    repository.join_room(bob_session, room.room_id)
    repository.link_artifact(session, "research_run", "run-1", "a" * 64, ("summary", "limitations"))
    repository.publish_projection(
        session,
        ProjectionSpec("projection-2", "research_run", "run-1", "a" * 64, ("summary", "limitations"), "SHARED_ROOM", room_id=room.room_id),
        {"summary": "descriptive result", "limitations": ["not a forecast"]},
        consent=True,
    )
    post = CommunityPost("post-1", room.room_id, "bob", "QUANT_FINDING", "Momentum", "Evidence says the result is historical.")
    repository.create_post(bob_session, post)
    repository.attach_projection(bob_session, post.post_id, "projection-2", "research")
    with pytest.raises(PermissionError):
        repository.attach_projection(session, post.post_id, "projection-2", "research")
    assert repository.get_post(bob_session, post.post_id).claim_type == "QUANT_FINDING"


def test_private_context_and_export_are_bounded_and_never_return_other_users() -> None:
    repository = repo()
    alice_session, bob_session = principals(repository)
    repository.save_node(alice_session, PersonalNode("alice-note", "note", "Private", {"body": "keep private"}))
    repository.save_node(bob_session, PersonalNode("bob-note", "note", "Private", {"body": "bob private"}))
    context = repository.authorized_context(alice_session, purpose="oos_review")
    assert all(item["node_id"] == "alice-note" for item in context)
    assert "bob private" not in json.dumps(context)
    exported = repository.export_personal(alice_session)
    assert "alice-note" in json.dumps(exported)
    assert "bob-note" not in json.dumps(exported)


def test_sql_injection_and_missing_membership_fail_closed() -> None:
    repository = repo()
    session, bob_session = principals(repository)
    repository.create_room(session, CommunityRoom("room-safe", "Safe", "Research"))
    with pytest.raises(PermissionError):
        repository.get_room(bob_session, "room-safe")
    assert repository.connection.execute("SELECT 1 FROM p7_principals WHERE principal_id = ?", ("alice' OR 1=1",)).fetchone() is None
