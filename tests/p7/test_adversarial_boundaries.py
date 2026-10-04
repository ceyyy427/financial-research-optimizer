from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta, timezone

import pytest

from finahinking.p7 import (
    CommunityPost,
    CommunityRoom,
    PersonalEdge,
    PersonalNode,
    Principal,
    ProjectionSpec,
    SQLiteP7Repository,
    apply_p7_migration,
)


def setup_repo() -> SQLiteP7Repository:
    connection = sqlite3.connect(":memory:")
    apply_p7_migration(connection)
    repository = SQLiteP7Repository(connection)
    repository.create_principal(Principal("alice", "Alice"))
    repository.create_principal(Principal("bob", "Bob"))
    repository.create_session("alice", "alice")
    repository.create_session("bob", "bob")
    return repository


def test_session_lifecycle_and_removed_membership_fail_closed() -> None:
    repository = setup_repo()
    repository.create_session("expired", "alice", "2000-01-01T00:00:00+00:00")
    with pytest.raises(PermissionError):
        repository.authorized_context("expired", purpose="test")
    repository.connection.execute("UPDATE p7_principals SET status = 'suspended' WHERE principal_id = ?", ("alice",))
    repository.connection.commit()
    with pytest.raises(PermissionError):
        repository.authorized_context("alice", purpose="test")
    repository.connection.execute("UPDATE p7_principals SET status = 'active' WHERE principal_id = ?", ("alice",))
    repository.connection.execute("UPDATE p7_sessions SET revoked = 1 WHERE session_id = ?", ("alice",))
    repository.connection.commit()
    with pytest.raises(PermissionError):
        repository.authorized_context("alice", purpose="test")

    repository.create_session("alice-2", "alice")
    repository.create_room("alice-2", CommunityRoom("room", "Room", "Test"))
    repository.connection.execute("UPDATE p7_room_members SET status = 'removed' WHERE room_id = ?", ("room",))
    repository.connection.commit()
    with pytest.raises(PermissionError):
        repository.get_room("alice-2", "room")


def test_duplicate_and_cross_owner_graph_writes_are_rejected() -> None:
    repository = setup_repo()
    repository.save_node("alice", PersonalNode("a", "note", "A", {"x": 1}))
    with pytest.raises(ValueError):
        repository.save_node("alice", PersonalNode("a", "note", "Duplicate", {"x": 2}))
    repository.save_node("bob", PersonalNode("b", "note", "B", {"x": 2}))
    with pytest.raises(PermissionError):
        repository.save_edge("alice", PersonalEdge("ab", "a", "b", "RELATED_TO"))


def test_export_fingerprint_is_canonical_and_tamper_evident() -> None:
    repository = setup_repo()
    repository.save_node("alice", PersonalNode("a", "note", "A", {"b": 2, "a": 1}))
    exported = repository.export_personal("alice")
    assert repository.validate_export_fingerprint(exported)
    exported["nodes"][0]["payload"]["a"] = 99
    assert not repository.validate_export_fingerprint(exported)


def test_room_projection_scope_and_role_escalation_fail_closed() -> None:
    repository = setup_repo()
    repository.create_room("alice", CommunityRoom("r1", "One", "Room one"))
    repository.create_room("alice", CommunityRoom("r2", "Two", "Room two"))
    repository.join_room("alice", "r1")
    assert repository.connection.execute("SELECT role FROM p7_room_members WHERE room_id = ? AND principal_id = ?", ("r1", "alice")).fetchone()["role"] == "owner"
    repository.join_room("bob", "r1")
    repository.join_room("bob", "r2")
    with pytest.raises(PermissionError):
        repository.join_room("bob", "r1", role="moderator")
    repository.link_artifact("alice", "research_run", "run-room", "a" * 64, ("summary",))
    repository.publish_projection(
        "alice",
        ProjectionSpec("p-room", "research_run", "run-room", "a" * 64, ("summary",), "SHARED_ROOM", room_id="r1"),
        {"summary": "bounded"},
        consent=True,
    )
    repository.create_post("bob", CommunityPost("post-r2", "r2", "bob", "QUANT_FINDING", "Other", "Different room."))
    with pytest.raises(PermissionError):
        repository.attach_projection("bob", "post-r2", "p-room", "research")
    repository.create_post("bob", CommunityPost("post-r1", "r1", "bob", "QUANT_FINDING", "Same", "Same room."))
    assert repository.get_public_projection("p-room", "bob").payload == {"summary": "bounded"}


def test_p7_migration_is_idempotent_and_exposes_room_scope() -> None:
    connection = sqlite3.connect(":memory:")
    apply_p7_migration(connection)
    apply_p7_migration(connection)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(p7_projections)").fetchall()}
    assert "room_id" in columns


def test_expiry_with_timezone_offset_is_compared_as_an_instant() -> None:
    repository = setup_repo()
    expired = (datetime.now(UTC) - timedelta(hours=1)).astimezone(timezone(timedelta(hours=14))).isoformat()
    with pytest.raises(PermissionError):
        repository.create_session("offset-expired", "alice", expired)
        repository.authorized_context("offset-expired", purpose="test")
