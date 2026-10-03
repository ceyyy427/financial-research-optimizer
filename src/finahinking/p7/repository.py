"""Privacy-first P7 persistence and authorization boundary.

The repository deliberately keeps P7 relational and boring: all authorization
decisions are made here, all SQL is parameterized, and callers receive only
objects owned by the authenticated principal (or explicitly projected).
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import (
    CommunityComment,
    CommunityPost,
    CommunityRoom,
    ConceptMasteryState,
    LearningThread,
    MasteryEvidence,
    PersonalEdge,
    PersonalNode,
    Principal,
    ProjectionSpec,
    PublicProjection,
)

MIGRATION_PATH = Path(__file__).resolve().parents[3] / "migrations" / "003_p7_personal_community.sql"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _expired(expires_at: str | None) -> bool:
    if not expires_at:
        return False
    try:
        value = datetime.fromisoformat(expires_at)
    except ValueError as exc:
        raise PermissionError("session expiry is malformed") from exc
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC) <= datetime.now(UTC)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _fingerprint(value: str, label: str = "source_fingerprint") -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ValueError(f"{label} must be a SHA-256 fingerprint")
    return value.lower()


def apply_p7_migration(connection: Any, *, dialect: str = "sqlite") -> None:
    """Install the additive P7 schema on SQLite or a DB-API PostgreSQL connection."""

    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    if dialect == "sqlite" and isinstance(connection, sqlite3.Connection):
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(sql)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(p7_projections)").fetchall()}
        if "room_id" not in columns:
            connection.execute("ALTER TABLE p7_projections ADD COLUMN room_id TEXT")
        connection.commit()
        return
    if dialect in {"postgres", "postgresql"} and hasattr(connection, "cursor"):
        cursor = connection.cursor()
        cursor.execute(sql)
        cursor.execute("ALTER TABLE p7_projections ADD COLUMN IF NOT EXISTS room_id TEXT REFERENCES p7_rooms(room_id) ON DELETE SET NULL")
        connection.commit()
        return
    raise ValueError("unsupported P7 migration dialect")


class SQLiteP7Repository:
    """SQLite adapter used by tests and local development.

    The same tables are portable to PostgreSQL.  No method interpolates an
    identifier or value into SQL; user-controlled strings are always bound.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("SQLiteP7Repository requires sqlite3.Connection")
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def _principal(self, session_id: str) -> str:
        row = self.connection.execute(
            "SELECT s.principal_id, s.expires_at, s.revoked, p.status "
            "FROM p7_sessions s JOIN p7_principals p ON p.principal_id = s.principal_id "
            "WHERE s.session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None or row["revoked"] or row["status"] != "active":
            raise PermissionError("session is not active")
        if _expired(row["expires_at"]):
            raise PermissionError("session is expired")
        return str(row["principal_id"])

    def _owner(self, session_id: str, owner_id: str) -> None:
        if self._principal(session_id) != owner_id:
            raise PermissionError("object is owned by another principal")

    def _audit(self, principal_id: str | None, action: str, object_type: str, object_id: str, detail: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO p7_audit_events (audit_id,principal_id,action,object_type,object_id,detail,created_at) VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), principal_id, action, object_type, object_id, _json(detail), _now()),
        )

    def create_principal(self, principal: Principal) -> Principal:
        try:
            self.connection.execute(
                "INSERT INTO p7_principals (principal_id,display_name,status,created_at) VALUES (?,?,?,?)",
                (principal.principal_id, principal.display_name, principal.status, _now()),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("principal violates database integrity") from exc
        return principal

    def create_session(self, session_id: str, principal_id: str, expires_at: str | None = None) -> str:
        self._require_text(session_id, "session_id")
        self._require_text(principal_id, "principal_id")
        try:
            self.connection.execute(
                "INSERT INTO p7_sessions (session_id,principal_id,created_at,expires_at) VALUES (?,?,?,?)",
                (session_id, principal_id, _now(), expires_at),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError("session violates database integrity") from exc
        return session_id

    def revoke_session(self, session_id: str) -> None:
        self.connection.execute("UPDATE p7_sessions SET revoked = 1 WHERE session_id = ?", (session_id,))
        self.connection.commit()

    @staticmethod
    def _require_text(value: str, label: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} is required")

    def save_node(self, session_id: str, node: PersonalNode) -> None:
        owner = self._principal(session_id)
        try:
            self.connection.execute(
                "INSERT INTO p7_personal_nodes (node_id,owner_id,node_type,title,payload,privacy_scope,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (node.node_id, owner, node.node_type, node.title, _json(node.payload), node.privacy_scope, _now(), _now()),
            )
            self._audit(owner, "create", "personal_node", node.node_id, {"node_type": node.node_type})
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("personal node violates database integrity") from exc

    def get_node(self, session_id: str, node_id: str) -> PersonalNode:
        self._principal(session_id)
        row = self.connection.execute("SELECT * FROM p7_personal_nodes WHERE node_id = ?", (node_id,)).fetchone()
        if row is None:
            raise KeyError(node_id)
        self._owner(session_id, row["owner_id"])
        return PersonalNode(row["node_id"], row["node_type"], row["title"], json.loads(row["payload"]), row["privacy_scope"])

    def update_node(self, session_id: str, node_id: str, payload: dict[str, Any]) -> PersonalNode:
        node = self.get_node(session_id, node_id)
        updated = PersonalNode(node.node_id, node.node_type, node.title, payload, node.privacy_scope)
        self.connection.execute(
            "UPDATE p7_personal_nodes SET payload = ?, updated_at = ? WHERE node_id = ? AND owner_id = ?",
            (_json(updated.payload), _now(), node_id, self._principal(session_id)),
        )
        self.connection.commit()
        return updated

    def save_edge(self, session_id: str, edge: PersonalEdge) -> None:
        owner = self._principal(session_id)
        source = self.connection.execute("SELECT owner_id FROM p7_personal_nodes WHERE node_id = ?", (edge.from_node_id,)).fetchone()
        target = self.connection.execute("SELECT owner_id FROM p7_personal_nodes WHERE node_id = ?", (edge.to_node_id,)).fetchone()
        if source is None or target is None or source["owner_id"] != owner or target["owner_id"] != owner:
            raise PermissionError("graph edge must connect nodes owned by the session principal")
        try:
            self.connection.execute(
                "INSERT INTO p7_personal_edges (edge_id,owner_id,from_node_id,to_node_id,relation_type,evidence_ids) VALUES (?,?,?,?,?,?)",
                (edge.edge_id, owner, edge.from_node_id, edge.to_node_id, edge.relation_type, _json(edge.evidence_ids)),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("personal edge violates database integrity") from exc

    def save_mastery_evidence(self, session_id: str, evidence: MasteryEvidence) -> None:
        owner = self._principal(session_id)
        concept = self.connection.execute("SELECT owner_id, node_type FROM p7_personal_nodes WHERE node_id = ?", (evidence.concept_id,)).fetchone()
        if concept is None:
            raise KeyError(evidence.concept_id)
        if concept["owner_id"] != owner:
            raise PermissionError("mastery evidence must reference a private concept owned by the principal")
        if concept["node_type"] != "concept":
            raise ValueError("mastery evidence must reference a concept node")
        try:
            self.connection.execute(
                "INSERT INTO p7_mastery_evidence (evidence_id,owner_id,concept_id,evidence_type,evidence_reference,outcome,observed_at,details) VALUES (?,?,?,?,?,?,?,?)",
                (evidence.evidence_id, owner, evidence.concept_id, evidence.evidence_type, evidence.evidence_reference, evidence.outcome, evidence.observed_at, _json(evidence.details)),
            )
            self._recompute_mastery(owner, evidence.concept_id)
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("mastery evidence violates database integrity") from exc

    def _recompute_mastery(self, owner: str, concept_id: str) -> None:
        rows = self.connection.execute(
            "SELECT evidence_id, outcome FROM p7_mastery_evidence WHERE owner_id = ? AND concept_id = ? ORDER BY observed_at, evidence_id",
            (owner, concept_id),
        ).fetchall()
        ids = tuple(str(row["evidence_id"]) for row in rows)
        outcomes = [str(row["outcome"]) for row in rows]
        if any(outcome == "incorrect" for outcome in outcomes) and "corrected" not in outcomes:
            state = "NEEDS_REVIEW"
            explanation = f"Needs review because evidence {ids[-1]} is incorrect; revisit the concept before reuse."
        elif not outcomes:
            state = "NEW"
            explanation = "No evidence has been recorded yet."
        elif any(outcome == "incorrect" for outcome in outcomes):
            state = "DEVELOPING"
            explanation = f"A correction is recorded; continue testing with evidence {', '.join(ids)}."
        elif len(outcomes) == 1:
            state = "EXPOSED"
            explanation = f"One evidence item ({ids[0]}) shows initial exposure."
        elif any(outcome in {"corrected", "correct"} for outcome in outcomes[2:]) and len(outcomes) >= 4:
            state = "ROBUST"
            explanation = f"Repeated correct and applied evidence supports robust mastery: {', '.join(ids)}."
        elif any(outcome == "correct" for outcome in outcomes[1:]):
            state = "APPLIED"
            explanation = f"More than one successful application is linked: {', '.join(ids)}."
        else:
            state = "DEVELOPING"
            explanation = f"Evidence is accumulating but needs another transfer check: {', '.join(ids)}."
        self.connection.execute(
            "INSERT INTO p7_mastery_states (owner_id,concept_id,state,evidence_count,evidence_ids,explanation,updated_at) VALUES (?,?,?,?,?,?,?) "
            "ON CONFLICT(owner_id,concept_id) DO UPDATE SET state=excluded.state,evidence_count=excluded.evidence_count,evidence_ids=excluded.evidence_ids,explanation=excluded.explanation,updated_at=excluded.updated_at",
            (owner, concept_id, state, len(ids), _json(ids), explanation, _now()),
        )

    def get_mastery_state(self, session_id: str, concept_id: str) -> ConceptMasteryState:
        owner = self._principal(session_id)
        concept = self.connection.execute("SELECT owner_id FROM p7_personal_nodes WHERE node_id = ?", (concept_id,)).fetchone()
        if concept is not None and concept["owner_id"] != owner:
            raise PermissionError("mastery state belongs to another principal")
        row = self.connection.execute("SELECT * FROM p7_mastery_states WHERE owner_id = ? AND concept_id = ?", (owner, concept_id)).fetchone()
        if row is None:
            return ConceptMasteryState(concept_id, "NEW", 0, (), "No evidence has been recorded yet.")
        return ConceptMasteryState(row["concept_id"], row["state"], int(row["evidence_count"]), tuple(json.loads(row["evidence_ids"])), row["explanation"])

    def create_learning_thread(self, session_id: str, thread: LearningThread) -> None:
        owner = self._principal(session_id)
        for node_id in thread.node_ids:
            self.get_node(session_id, node_id)
        try:
            self.connection.execute("INSERT INTO p7_learning_threads (thread_id,owner_id,title,status,created_at) VALUES (?,?,?,?,?)", (thread.thread_id, owner, thread.title, thread.status, _now()))
            self.connection.executemany("INSERT INTO p7_learning_thread_items (thread_id,node_id,position) VALUES (?,?,?)", [(thread.thread_id, node_id, pos) for pos, node_id in enumerate(thread.node_ids)])
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("learning thread violates database integrity") from exc

    def save_history_entry(self, session_id: str, *, history_id: str, source_kind: str, source_id: str, source_fingerprint: str, event_type: str, title: str, occurred_at: str, limitations: list[str] | tuple[str, ...] = ()) -> None:
        owner = self._principal(session_id)
        source_fingerprint = _fingerprint(source_fingerprint)
        self.connection.execute(
            "INSERT INTO p7_history_entries (history_id,owner_id,source_kind,source_id,source_fingerprint,event_type,title,occurred_at,limitations) VALUES (?,?,?,?,?,?,?,?,?)",
            (history_id, owner, source_kind, source_id, source_fingerprint, event_type, title, occurred_at, _json(list(limitations))),
        )
        self.connection.commit()

    def save_object(self, session_id: str, *, saved_id: str, source_kind: str, source_id: str, source_fingerprint: str, note: str) -> None:
        """Save an explicit private workspace reference, never a copied truth."""
        owner = self._principal(session_id)
        source_fingerprint = _fingerprint(source_fingerprint)
        self.connection.execute(
            "INSERT INTO p7_saved_objects (saved_id,owner_id,source_kind,source_id,source_fingerprint,note,created_at) VALUES (?,?,?,?,?,?,?)",
            (saved_id, owner, source_kind, source_id, source_fingerprint, note, _now()),
        )
        self.connection.commit()

    def list_saved_objects(self, session_id: str) -> list[dict[str, Any]]:
        owner = self._principal(session_id)
        return [dict(row) for row in self.connection.execute("SELECT saved_id,source_kind,source_id,source_fingerprint,note,created_at FROM p7_saved_objects WHERE owner_id = ? ORDER BY created_at,saved_id", (owner,)).fetchall()]

    def link_artifact(self, session_id: str, source_kind: str, source_id: str, source_fingerprint: str, allowed_fields: tuple[str, ...] | list[str], *, code_commit: str | None = None) -> None:
        owner = self._principal(session_id)
        source_fingerprint = _fingerprint(source_fingerprint)
        fields = tuple(dict.fromkeys(str(field) for field in allowed_fields))
        if not fields:
            raise ValueError("allowed_fields are required")
        self.connection.execute(
            "INSERT INTO p7_artifact_links (link_id,owner_id,source_kind,source_id,source_fingerprint,allowed_fields,current_fingerprint,code_commit,created_at) VALUES (?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(owner_id,source_kind,source_id) DO UPDATE SET source_fingerprint=excluded.source_fingerprint,allowed_fields=excluded.allowed_fields,current_fingerprint=excluded.current_fingerprint,code_commit=excluded.code_commit",
            (str(uuid.uuid4()), owner, source_kind, source_id, source_fingerprint, _json(fields), source_fingerprint, code_commit, _now()),
        )
        self.connection.commit()

    def save_strategy_version(
        self,
        session_id: str,
        *,
        strategy_version_id: str,
        strategy_id: str,
        strategy_fingerprint: str,
        feature_fingerprint: str | None = None,
        backtest_fingerprint: str | None = None,
        oos_fingerprint: str | None = None,
        paper_fingerprint: str | None = None,
        limitations: tuple[str, ...] | list[str] = (),
        code_commit: str | None = None,
    ) -> None:
        owner = self._principal(session_id)
        strategy_fingerprint = _fingerprint(strategy_fingerprint, "strategy_fingerprint")
        feature_fingerprint = _fingerprint(feature_fingerprint, "feature_fingerprint") if feature_fingerprint is not None else None
        backtest_fingerprint = _fingerprint(backtest_fingerprint, "backtest_fingerprint") if backtest_fingerprint is not None else None
        oos_fingerprint = _fingerprint(oos_fingerprint, "oos_fingerprint") if oos_fingerprint is not None else None
        paper_fingerprint = _fingerprint(paper_fingerprint, "paper_fingerprint") if paper_fingerprint is not None else None
        self.connection.execute(
            "INSERT INTO p7_strategy_versions (strategy_version_id,owner_id,strategy_id,strategy_fingerprint,feature_fingerprint,backtest_fingerprint,oos_fingerprint,paper_fingerprint,limitations,code_commit,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (strategy_version_id, owner, strategy_id, strategy_fingerprint, feature_fingerprint, backtest_fingerprint, oos_fingerprint, paper_fingerprint, _json(list(limitations)), code_commit, _now()),
        )
        self.connection.commit()

    def list_strategy_versions(self, session_id: str, *, strategy_id: str | None = None) -> list[dict[str, Any]]:
        owner = self._principal(session_id)
        if strategy_id is None:
            rows = self.connection.execute("SELECT * FROM p7_strategy_versions WHERE owner_id = ? ORDER BY created_at, strategy_version_id", (owner,)).fetchall()
        else:
            rows = self.connection.execute("SELECT * FROM p7_strategy_versions WHERE owner_id = ? AND strategy_id = ? ORDER BY created_at, strategy_version_id", (owner, strategy_id)).fetchall()
        return [{**dict(row), "limitations": json.loads(row["limitations"])} for row in rows]

    def publish_projection(self, session_id: str, spec: ProjectionSpec, payload: dict[str, Any], *, consent: bool) -> PublicProjection:
        owner = self._principal(session_id)
        link = self.connection.execute(
            "SELECT * FROM p7_artifact_links WHERE owner_id = ? AND source_kind = ? AND source_id = ?",
            (owner, spec.source_kind, spec.source_id),
        ).fetchone()
        if not consent:
            raise PermissionError("explicit projection consent is required")
        if spec.visibility == "SHARED_ROOM":
            room = self.connection.execute("SELECT status FROM p7_rooms WHERE room_id = ?", (spec.room_id,)).fetchone()
            if room is None or room["status"] != "active" or not self._is_member(owner, spec.room_id):
                raise PermissionError("room projection requires an active room membership")
        if link is None or link["current_fingerprint"] != spec.source_fingerprint:
            raise PermissionError("projection source fingerprint is not current and owned")
        allowed = set(json.loads(link["allowed_fields"]))
        if any(field not in allowed for field in spec.fields):
            raise PermissionError("projection field is not allow-listed")
        sanitized = {field: payload[field] for field in spec.fields if field in payload}
        if not sanitized:
            raise ValueError("projection contains no allowed payload fields")
        try:
            self.connection.execute(
                "INSERT INTO p7_projections (projection_id,owner_id,source_kind,source_id,source_fingerprint,fields,visibility,room_id,status,version,payload,limitations,consented_at,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (spec.projection_id, owner, spec.source_kind, spec.source_id, spec.source_fingerprint, _json(spec.fields), spec.visibility, spec.room_id, "ACTIVE", spec.version, _json(sanitized), _json(spec.limitations), _now(), _now()),
            )
            self._audit(owner, "publish", "projection", spec.projection_id, {"visibility": spec.visibility, "fields": spec.fields})
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("projection violates database integrity") from exc
        return PublicProjection(spec.projection_id, owner, spec.visibility, "ACTIVE", spec.version, sanitized, spec.source_fingerprint, spec.limitations)

    def get_public_projection(self, projection_id: str, session_id: str | None = None) -> PublicProjection:
        # Accept the natural ``(session_id, projection_id)`` order as well as
        # the public ``(projection_id, session_id=None)`` form.  This keeps
        # anonymous reads ergonomic while making authenticated reads hard to
        # accidentally omit from callers that already carry a session first.
        if session_id is not None:
            first_is_session = self.connection.execute("SELECT 1 FROM p7_sessions WHERE session_id = ?", (projection_id,)).fetchone() is not None
            second_is_projection = self.connection.execute("SELECT 1 FROM p7_projections WHERE projection_id = ?", (session_id,)).fetchone() is not None
            if first_is_session and second_is_projection:
                projection_id, session_id = session_id, projection_id
        row = self.connection.execute("SELECT * FROM p7_projections WHERE projection_id = ?", (projection_id,)).fetchone()
        if row is None:
            raise KeyError(projection_id)
        if row["status"] != "ACTIVE":
            raise PermissionError("projection is no longer active")
        if session_id is None:
            if row["visibility"] != "PUBLIC":
                raise PermissionError("projection is not public")
        else:
            principal = self._principal(session_id)
            if row["visibility"] == "SHARED_ROOM":
                room = self.connection.execute("SELECT status FROM p7_rooms WHERE room_id = ?", (row["room_id"],)).fetchone()
                if room is None or room["status"] != "active":
                    raise PermissionError("projection room is not active")
            if principal != row["owner_id"] and row["visibility"] != "PUBLIC" and (row["visibility"] != "SHARED_ROOM" or not row["room_id"] or not self._is_member(principal, row["room_id"])):
                raise PermissionError("projection is not visible to this principal")
        return PublicProjection(row["projection_id"], row["owner_id"], row["visibility"], row["status"], int(row["version"]), json.loads(row["payload"]), row["source_fingerprint"], tuple(json.loads(row["limitations"])))

    def revoke_projection(self, session_id: str, projection_id: str) -> None:
        owner = self._principal(session_id)
        row = self.connection.execute("SELECT owner_id FROM p7_projections WHERE projection_id = ?", (projection_id,)).fetchone()
        if row is None:
            raise KeyError(projection_id)
        self._owner(session_id, row["owner_id"])
        self.connection.execute("UPDATE p7_projections SET status = 'REVOKED', revoked_at = ? WHERE projection_id = ? AND owner_id = ?", (_now(), projection_id, owner))
        self._audit(owner, "revoke", "projection", projection_id, {})
        self.connection.commit()

    def refresh_stale_projections(self, session_id: str) -> int:
        owner = self._principal(session_id)
        rows = self.connection.execute("SELECT p.projection_id, p.source_kind, p.source_id, p.source_fingerprint, a.current_fingerprint FROM p7_projections p JOIN p7_artifact_links a ON a.owner_id = p.owner_id AND a.source_kind = p.source_kind AND a.source_id = p.source_id WHERE p.owner_id = ? AND p.status = 'ACTIVE'", (owner,)).fetchall()
        changed = 0
        for row in rows:
            if row["source_fingerprint"] != row["current_fingerprint"]:
                self.connection.execute("UPDATE p7_projections SET status = 'STALE' WHERE projection_id = ?", (row["projection_id"],))
                changed += 1
        self.connection.commit()
        return changed

    def create_room(self, session_id: str, room: CommunityRoom) -> None:
        owner = self._principal(session_id)
        try:
            self.connection.execute("INSERT INTO p7_rooms (room_id,slug,name,description,status,created_at) VALUES (?,?,?,?,?,?)", (room.room_id, room.slug, room.name, room.description, "active", _now()))
            self.connection.execute("INSERT INTO p7_room_members (room_id,principal_id,role,status,created_at) VALUES (?,?,?,?,?)", (room.room_id, owner, "owner", "active", _now()))
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("room violates database integrity") from exc

    def join_room(self, session_id: str, room_id: str, *, role: str = "member") -> None:
        principal = self._principal(session_id)
        if role not in {"member", "moderator"}:
            raise ValueError("invalid room role")
        room = self.connection.execute("SELECT status FROM p7_rooms WHERE room_id = ?", (room_id,)).fetchone()
        if room is None or room["status"] != "active":
            raise PermissionError("room is not active")
        if role == "moderator":
            owner = self.connection.execute("SELECT principal_id FROM p7_room_members WHERE room_id = ? AND role = 'owner' AND status = 'active'", (room_id,)).fetchone()
            if owner is None or owner["principal_id"] != principal:
                raise PermissionError("only the room owner may assign moderator role")
        existing = self.connection.execute("SELECT role,status FROM p7_room_members WHERE room_id = ? AND principal_id = ?", (room_id, principal)).fetchone()
        if existing is not None and existing["role"] == "owner" and existing["status"] == "active":
            return
        self.connection.execute("INSERT OR REPLACE INTO p7_room_members (room_id,principal_id,role,status,created_at) VALUES (?,?,?,?,?)", (room_id, principal, role, "active", _now()))
        self.connection.commit()

    def _is_member(self, principal_id: str, room_id: str) -> bool:
        row = self.connection.execute("SELECT 1 FROM p7_room_members WHERE room_id = ? AND principal_id = ? AND status = 'active'", (room_id, principal_id)).fetchone()
        return row is not None

    def get_room(self, session_id: str, room_id: str) -> CommunityRoom:
        principal = self._principal(session_id)
        row = self.connection.execute("SELECT * FROM p7_rooms WHERE room_id = ?", (room_id,)).fetchone()
        if row is None:
            raise KeyError(room_id)
        if not self._is_member(principal, room_id):
            raise PermissionError("room membership is required")
        return CommunityRoom(row["room_id"], row["name"], row["description"], row["slug"])

    def create_post(self, session_id: str, post: CommunityPost) -> None:
        principal = self._principal(session_id)
        if principal != post.author_id or not self._is_member(principal, post.room_id):
            raise PermissionError("only an active room member can author a post")
        try:
            self.connection.execute("INSERT INTO p7_posts (post_id,room_id,author_id,claim_type,title,body,status,created_at) VALUES (?,?,?,?,?,?,?,?)", (post.post_id, post.room_id, post.author_id, post.claim_type, post.title, post.body, post.status, _now()))
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("post violates database integrity") from exc

    def get_post(self, session_id: str, post_id: str) -> CommunityPost:
        principal = self._principal(session_id)
        row = self.connection.execute("SELECT * FROM p7_posts WHERE post_id = ?", (post_id,)).fetchone()
        if row is None:
            raise KeyError(post_id)
        if not self._is_member(principal, row["room_id"]):
            raise PermissionError("room membership is required")
        return CommunityPost(row["post_id"], row["room_id"], row["author_id"], row["claim_type"], row["title"], row["body"], row["status"])

    def attach_projection(self, session_id: str, post_id: str, projection_id: str, role: str) -> None:
        principal = self._principal(session_id)
        post = self.connection.execute("SELECT author_id, room_id FROM p7_posts WHERE post_id = ?", (post_id,)).fetchone()
        projection = self.connection.execute("SELECT owner_id, visibility, room_id, status FROM p7_projections WHERE projection_id = ?", (projection_id,)).fetchone()
        if post is None or projection is None:
            raise KeyError(post_id if post is None else projection_id)
        if principal != post["author_id"] or not self._is_member(principal, post["room_id"]):
            raise PermissionError("only the post author may attach evidence")
        if projection["status"] != "ACTIVE" or projection["visibility"] not in {"SHARED_ROOM", "PUBLIC"}:
            raise PermissionError("only an active room/public projection may be attached")
        if projection["visibility"] == "SHARED_ROOM" and (not projection["room_id"] or projection["room_id"] != post["room_id"]):
            raise PermissionError("room projection cannot be attached across rooms")
        self.connection.execute("INSERT INTO p7_projection_attachments (attachment_id,post_id,projection_id,role,created_at) VALUES (?,?,?,?,?)", (str(uuid.uuid4()), post_id, projection_id, role, _now()))
        self.connection.commit()

    def add_comment(self, session_id: str, comment: CommunityComment) -> None:
        principal = self._principal(session_id)
        post = self.connection.execute("SELECT room_id FROM p7_posts WHERE post_id = ?", (comment.post_id,)).fetchone()
        if post is None:
            raise KeyError(comment.post_id)
        if principal != comment.author_id or not self._is_member(principal, post["room_id"]):
            raise PermissionError("only a room member can comment")
        self.connection.execute("INSERT INTO p7_comments (comment_id,post_id,author_id,body,status,created_at) VALUES (?,?,?,?,?,?)", (comment.comment_id, comment.post_id, comment.author_id, comment.body, comment.status, _now()))
        self.connection.commit()

    def save_as_question(self, session_id: str, post_id: str, node_id: str, title: str) -> PersonalNode:
        post = self.get_post(session_id, post_id)
        node = PersonalNode(node_id, "question", title, {"from_post_id": post.post_id, "claim_type": post.claim_type, "body": post.body})
        self.save_node(session_id, node)
        return node

    def authorized_context(self, session_id: str, *, purpose: str, limit: int = 50) -> list[dict[str, Any]]:
        owner = self._principal(session_id)
        bounded = max(1, min(int(limit), 100))
        rows = self.connection.execute("SELECT node_id,node_type,title,payload,updated_at FROM p7_personal_nodes WHERE owner_id = ? ORDER BY updated_at DESC,node_id LIMIT ?", (owner, bounded)).fetchall()
        return [{"node_id": row["node_id"], "node_type": row["node_type"], "title": row["title"], "payload": json.loads(row["payload"]), "updated_at": row["updated_at"], "purpose": purpose} for row in rows]

    def export_personal(self, session_id: str) -> dict[str, Any]:
        owner = self._principal(session_id)
        nodes = [dict(row) for row in self.connection.execute("SELECT node_id,node_type,title,payload,privacy_scope,created_at,updated_at FROM p7_personal_nodes WHERE owner_id = ? ORDER BY node_id", (owner,)).fetchall()]
        for row in nodes:
            row["payload"] = json.loads(row["payload"])
        edges = [dict(row) for row in self.connection.execute("SELECT edge_id,from_node_id,to_node_id,relation_type,evidence_ids FROM p7_personal_edges WHERE owner_id = ? ORDER BY edge_id", (owner,)).fetchall()]
        for row in edges:
            row["evidence_ids"] = json.loads(row["evidence_ids"])
        mastery = [dict(row) for row in self.connection.execute("SELECT concept_id,state,evidence_count,evidence_ids,explanation,updated_at FROM p7_mastery_states WHERE owner_id = ? ORDER BY concept_id", (owner,)).fetchall()]
        for row in mastery:
            row["evidence_ids"] = json.loads(row["evidence_ids"])
        mastery_evidence = [dict(row) for row in self.connection.execute("SELECT evidence_id,concept_id,evidence_type,evidence_reference,outcome,observed_at,details FROM p7_mastery_evidence WHERE owner_id = ? ORDER BY evidence_id", (owner,)).fetchall()]
        for row in mastery_evidence:
            row["details"] = json.loads(row["details"])
        projections = [dict(row) for row in self.connection.execute("SELECT projection_id,source_kind,source_id,source_fingerprint,fields,visibility,room_id,status,version,payload,limitations,consented_at,revoked_at,created_at FROM p7_projections WHERE owner_id = ? ORDER BY projection_id", (owner,)).fetchall()]
        for row in projections:
            row["fields"], row["payload"], row["limitations"] = json.loads(row["fields"]), json.loads(row["payload"]), json.loads(row["limitations"])
        history = [dict(row) for row in self.connection.execute("SELECT history_id,source_kind,source_id,source_fingerprint,event_type,title,occurred_at,limitations FROM p7_history_entries WHERE owner_id = ? ORDER BY occurred_at,history_id", (owner,)).fetchall()]
        for row in history:
            row["limitations"] = json.loads(row["limitations"])
        threads = [dict(row) for row in self.connection.execute("SELECT thread_id,title,status,created_at FROM p7_learning_threads WHERE owner_id = ? ORDER BY thread_id", (owner,)).fetchall()]
        for row in threads:
            row["node_ids"] = [item["node_id"] for item in self.connection.execute("SELECT node_id FROM p7_learning_thread_items WHERE thread_id = ? ORDER BY position", (row["thread_id"],)).fetchall()]
        strategy_history = [dict(row) for row in self.connection.execute("SELECT strategy_version_id,strategy_id,strategy_fingerprint,feature_fingerprint,backtest_fingerprint,oos_fingerprint,paper_fingerprint,limitations,code_commit,created_at FROM p7_strategy_versions WHERE owner_id = ? ORDER BY strategy_version_id", (owner,)).fetchall()]
        for row in strategy_history:
            row["limitations"] = json.loads(row["limitations"])
        saved_objects = [dict(row) for row in self.connection.execute("SELECT saved_id,source_kind,source_id,source_fingerprint,note,created_at FROM p7_saved_objects WHERE owner_id = ? ORDER BY saved_id", (owner,)).fetchall()]
        artifact_links = [dict(row) for row in self.connection.execute("SELECT link_id,source_kind,source_id,source_fingerprint,allowed_fields,current_fingerprint,code_commit,created_at FROM p7_artifact_links WHERE owner_id = ? ORDER BY link_id", (owner,)).fetchall()]
        for row in artifact_links:
            row["allowed_fields"] = json.loads(row["allowed_fields"])
        export = {"principal_id": owner, "nodes": nodes, "edges": edges, "mastery": mastery, "mastery_evidence": mastery_evidence, "history": history, "learning_threads": threads, "strategy_history": strategy_history, "saved_objects": saved_objects, "artifact_links": artifact_links, "projections": projections}
        export["export_fingerprint"] = hashlib.sha256(_json(export).encode("utf-8")).hexdigest()
        return export

    @staticmethod
    def validate_export_fingerprint(export: dict[str, Any]) -> bool:
        """Check a canonical export before an operator stores or replays it."""

        if not isinstance(export, dict) or not isinstance(export.get("export_fingerprint"), str):
            return False
        candidate = dict(export)
        fingerprint = candidate.pop("export_fingerprint")
        return hashlib.sha256(_json(candidate).encode("utf-8")).hexdigest() == fingerprint

    def delete_personal(self, session_id: str) -> None:
        owner = self._principal(session_id)
        self.connection.execute("UPDATE p7_projections SET status = 'REVOKED', revoked_at = ? WHERE owner_id = ? AND status != 'REVOKED'", (_now(), owner))
        self.connection.execute("DELETE FROM p7_saved_objects WHERE owner_id = ?", (owner,))
        self.connection.execute("DELETE FROM p7_history_entries WHERE owner_id = ?", (owner,))
        self.connection.execute("DELETE FROM p7_artifact_links WHERE owner_id = ?", (owner,))
        self.connection.execute("DELETE FROM p7_strategy_versions WHERE owner_id = ?", (owner,))
        self.connection.execute("DELETE FROM p7_misconceptions WHERE owner_id = ?", (owner,))
        self.connection.execute("DELETE FROM p7_learning_threads WHERE owner_id = ?", (owner,))
        self.connection.execute("DELETE FROM p7_personal_nodes WHERE owner_id = ?", (owner,))
        self._audit(owner, "delete_personal", "principal", owner, {"retained": "audit_only", "private_records": "deleted", "shared_projections": "revoked"})
        self.connection.commit()


__all__ = ["MIGRATION_PATH", "SQLiteP7Repository", "apply_p7_migration"]
