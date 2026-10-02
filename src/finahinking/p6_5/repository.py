"""Parameterized P6.5 persistence with a deterministic SQLite test adapter."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import (
    Claim,
    ClaimEvidenceLink,
    Concept,
    Event,
    Evidence,
    Observation,
    Source,
    SourceEndpoint,
    SourceRelease,
    TransportCapture,
)

MIGRATION_PATH = Path(__file__).resolve().parents[3] / "migrations" / "001_p6_5_understanding.sql"
ADDITIVE_MIGRATION_PATHS = (
    MIGRATION_PATH,
    Path(__file__).resolve().parents[3] / "migrations" / "002_p6_6_strategy_lab.sql",
)
_SAFE_ARTIFACT_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def apply_migration(connection: sqlite3.Connection, *, dialect: str = "sqlite") -> None:
    if dialect not in {"sqlite", "postgres"}:
        raise ValueError("unsupported migration dialect")
    sql = "\n".join(path.read_text(encoding="utf-8") for path in ADDITIVE_MIGRATION_PATHS if path.is_file())
    if isinstance(connection, sqlite3.Connection):
        connection.executescript("PRAGMA foreign_keys = ON;\n" + sql)
        connection.commit()
        return
    cursor = connection.cursor()
    cursor.execute(sql)
    connection.commit()


class SQLiteUnderstandingRepository:
    """A test/dev repository; production schema is the PostgreSQL migration."""

    def __init__(self, connection: sqlite3.Connection, *, artifact_root: str | Path) -> None:
        if not isinstance(connection, sqlite3.Connection):
            raise TypeError("SQLiteUnderstandingRepository requires sqlite3.Connection")
        self.connection = connection
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.artifact_root = Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def _insert(self, sql: str, values: tuple[Any, ...], label: str) -> None:
        try:
            self.connection.execute(sql, values)
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"{label} violates database integrity") from exc

    def save_source(self, source: Source) -> None:
        self._insert("INSERT INTO p6_5_sources (source_id,name,publisher,tier,canonical_url,underlying_source,owner,access_method,usage_conditions,authentication,decision,source_fingerprint,admitted_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (source.source_id, source.name, source.publisher, source.tier.value, source.canonical_url, source.underlying_source, source.owner, source.access_method, source.usage_conditions, source.authentication, source.decision.value, source.fingerprint, source.admitted_at), "source")

    def save_endpoint(self, endpoint: SourceEndpoint) -> None:
        self._insert("INSERT INTO p6_5_endpoints (endpoint_id,source_id,url,method,content_type,rate_limit,historical_support,revision_support,available_at_semantics,active) VALUES (?,?,?,?,?,?,?,?,?,?)", (endpoint.endpoint_id, endpoint.source_id, endpoint.url, endpoint.method, endpoint.content_type, endpoint.rate_limit, int(endpoint.historical_support), endpoint.revision_support, endpoint.available_at_semantics, int(endpoint.active)), "endpoint")

    def save_release(self, release: SourceRelease) -> None:
        self._insert("INSERT INTO p6_5_releases (release_id,source_id,endpoint_id,event_type,reference_period,published_at,available_at,release_url,schedule_fingerprint) VALUES (?,?,?,?,?,?,?,?,?)", (release.release_id, release.source_id, release.endpoint_id, release.event_type, release.reference_period, release.published_at, release.available_at, release.release_url, release.schedule_fingerprint), "release")

    def save_capture(self, capture: TransportCapture) -> None:
        if capture.raw_payload is None:
            raise ValueError("capture raw payload is required for persistence")
        if not _SAFE_ARTIFACT_ID.fullmatch(capture.raw_artifact_id):
            raise ValueError("artifact id is invalid")
        payload_bytes = capture.raw_payload.encode("utf-8")
        if hashlib.sha256(payload_bytes).hexdigest() != capture.payload_hash:
            raise ValueError("capture payload hash does not match raw payload")
        path = self.artifact_root / f"{capture.raw_artifact_id}.bin"
        if path.parent != self.artifact_root:
            raise ValueError("artifact path escapes storage root")
        if path.exists():
            raise ValueError("artifact path already exists")
        fd, temporary = tempfile.mkstemp(prefix=f".{capture.raw_artifact_id}.", suffix=".tmp", dir=self.artifact_root)
        installed = False
        committed = False
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            # Keep the artifact write and both relational rows in one unit.  A
            # duplicate capture must not leave an orphan artifact behind.
            self.connection.execute("BEGIN")
            self.connection.execute(
                "INSERT INTO p6_5_artifacts (artifact_id,payload_hash,storage_path,byte_length,created_at) VALUES (?,?,?,?,?)",
                (capture.raw_artifact_id, capture.payload_hash, str(path), len(payload_bytes), datetime.now(UTC).isoformat()),
            )
            self.connection.execute(
                "INSERT INTO p6_5_captures (capture_id,source_id,endpoint_id,request_fingerprint,retrieved_at,first_observed_at,status,content_type,relevant_headers,raw_artifact_id,payload_hash,parser_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (capture.capture_id, capture.source_id, capture.endpoint_id, capture.request_fingerprint, capture.retrieved_at, capture.first_observed_at, capture.status, capture.content_type, json.dumps(capture.relevant_headers, sort_keys=True), capture.raw_artifact_id, capture.payload_hash, capture.parser_version),
            )
            os.replace(temporary, path)
            installed = True
            self.connection.commit()
            committed = True
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("capture violates database integrity") from exc
        except Exception:
            self.connection.rollback()
            raise
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
            if installed and not committed and path.exists():
                # The database commit is the authority.  If it failed, remove
                # the newly installed file so the filesystem cannot drift.
                path.unlink()

    def save_observation(self, observation: Observation) -> None:
        dimensions = json.dumps(observation.dimensions, sort_keys=True, separators=(",", ":"))
        try:
            self.connection.execute("INSERT INTO p6_5_observations (observation_id,source_id,series_id,reference_period,dimensions) VALUES (?,?,?,?,?)", (observation.observation_id, observation.source_id, observation.series_id, observation.reference_period, dimensions))
            for version in observation.versions:
                self.connection.execute("INSERT INTO p6_5_observation_versions (version_id,observation_id,value,unit,occurred_at,effective_at,published_at,available_at,retrieved_at,capture_id,revision_status,supersedes_version_id,footnotes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (version.version_id, observation.observation_id, version.value, version.unit, version.occurred_at, version.effective_at, version.published_at, version.available_at, version.retrieved_at, version.capture_id, version.revision_status.value, version.supersedes_version_id, json.dumps(version.footnotes)))
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("observation version violates database integrity") from exc

    def save_event(self, event: Event) -> None:
        try:
            self.connection.execute("INSERT INTO p6_5_events (event_id,event_type,source_id,reference_period,occurred_at,effective_at,published_at,available_at,revision_status,fingerprint) VALUES (?,?,?,?,?,?,?,?,?,?)", (event.event_id, event.event_type, event.source_id, event.reference_period, event.occurred_at, event.effective_at, event.published_at, event.available_at, event.revision_status.value, event.fingerprint))
            for observation_id in event.observation_ids:
                self.connection.execute("INSERT INTO p6_5_event_observations (event_id,observation_id) VALUES (?,?)", (event.event_id, observation_id))
            for evidence_id in event.evidence_ids:
                self.connection.execute("INSERT INTO p6_5_event_evidence (event_id,evidence_id) VALUES (?,?)", (event.event_id, evidence_id))
            self.connection.commit()
        except sqlite3.IntegrityError as exc:
            self.connection.rollback()
            raise ValueError("event link violates database integrity") from exc

    def save_evidence(self, evidence: Evidence) -> None:
        self._insert("INSERT INTO p6_5_evidence (evidence_id,evidence_type,source_id,capture_id,reference,status,scope,limitations,source_fingerprint) VALUES (?,?,?,?,?,?,?,?,?)", (evidence.evidence_id, evidence.evidence_type, evidence.source_id, evidence.capture_id, evidence.reference, evidence.status.value, evidence.scope, json.dumps(evidence.limitations), evidence.source_fingerprint), "evidence")

    def save_claim(self, claim: Claim) -> None:
        linked = [
            self.connection.execute("SELECT source_fingerprint FROM p6_5_evidence WHERE evidence_id = ?", (evidence_id,)).fetchone()
            for evidence_id in claim.evidence_ids
        ]
        missing = [evidence_id for evidence_id, row in zip(claim.evidence_ids, linked) if row is None]
        if missing:
            raise ValueError("claim violates foreign key evidence references")
        if claim.source_verified and not any(row[0] == claim.source_fingerprint for row in linked if row and row[0]):
            raise ValueError("claim fingerprint does not match stored evidence")
        self._insert("INSERT INTO p6_5_claims (claim_id,claim_type,text,evidence_status,source_fingerprint,source_verified,limitations) VALUES (?,?,?,?,?,?,?)", (claim.claim_id, claim.claim_type.value, claim.text, claim.evidence_status.value, claim.source_fingerprint, int(claim.source_verified), json.dumps(claim.limitations)), "claim")

    def link_claim_evidence(self, link: ClaimEvidenceLink) -> None:
        self._insert("INSERT INTO p6_5_claim_evidence (claim_id,evidence_id,support_type,scope,limitations) VALUES (?,?,?,?,?)", (link.claim_id, link.evidence_id, link.support_type.value, link.scope, json.dumps(link.limitations)), "claim evidence link")

    def save_concept(self, concept: Concept) -> None:
        self._insert(
            "INSERT INTO p6_5_concepts (concept_id,name,definition,formula,evidence_ids) VALUES (?,?,?,?,?)",
            (concept.concept_id, concept.name, concept.definition, concept.formula, json.dumps(concept.evidence_ids)),
            "concept",
        )

    def save_learning_ref(self, *, learning_ref_id: str, event_id: str, evidence_id: str, concept_id: str | None, card_fingerprint: str, user_id: str) -> None:
        self._insert(
            "INSERT INTO p6_5_learning_refs (learning_ref_id,event_id,evidence_id,concept_id,card_fingerprint,user_id) VALUES (?,?,?,?,?,?)",
            (learning_ref_id, event_id, evidence_id, concept_id, card_fingerprint, user_id),
            "learning reference",
        )

    def show_evidence(self, claim_id: str) -> list[dict[str, Any]]:
        rows = self.connection.execute("SELECT ce.claim_id, ce.support_type, ce.scope, c.text, c.claim_type, e.evidence_id, e.evidence_type, e.reference, e.status, e.scope AS evidence_scope, e.limitations, s.publisher, s.canonical_url, cp.capture_id, cp.retrieved_at, cp.first_observed_at, cp.raw_artifact_id FROM p6_5_claim_evidence ce JOIN p6_5_claims c ON c.claim_id = ce.claim_id JOIN p6_5_evidence e ON e.evidence_id = ce.evidence_id JOIN p6_5_sources s ON s.source_id = e.source_id LEFT JOIN p6_5_captures cp ON cp.capture_id = e.capture_id WHERE ce.claim_id = ? ORDER BY e.evidence_id", (claim_id,)).fetchall()
        columns = [column[0] for column in self.connection.execute("SELECT ce.claim_id, ce.support_type, ce.scope, c.text, c.claim_type, e.evidence_id, e.evidence_type, e.reference, e.status, e.scope AS evidence_scope, e.limitations, s.publisher, s.canonical_url, cp.capture_id, cp.retrieved_at, cp.first_observed_at, cp.raw_artifact_id FROM p6_5_claim_evidence ce JOIN p6_5_claims c ON c.claim_id = ce.claim_id JOIN p6_5_evidence e ON e.evidence_id = ce.evidence_id JOIN p6_5_sources s ON s.source_id = e.source_id LEFT JOIN p6_5_captures cp ON cp.capture_id = e.capture_id WHERE ce.claim_id = ? LIMIT 0", (claim_id,)).description]
        return [dict(zip(columns, row)) for row in rows]


__all__ = ["MIGRATION_PATH", "SQLiteUnderstandingRepository", "apply_migration"]
