"""Small, offline-first local application shell for Finahinking.

The shell deliberately contains no domain logic or provider credentials.  It
adapts the existing P7 repository and exposes deterministic HTML/JSON routes
for the event, knowledge, quant, strategy, personal, and community journeys.
The same object can be mounted in the stdlib HTTP server or exercised directly
by tests, which keeps the local runtime inspectable and inexpensive to run.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import sqlite3
import tempfile
import threading
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from finahinking.p7 import (
    CommunityClaim,
    CommunityIntegrityService,
    CommunityPost,
    CommunityRoom,
    EventLearningAdapter,
    MasteryEvidence,
    PersonalNode,
    Principal,
    ProjectionSpec,
    SQLiteP7Repository,
    apply_p7_migration,
)
from finahinking.p7_5.knowledge import DEFAULT_CATALOG


def default_db_path() -> str:
    """Return the user-local SQLite path used by a normal first run."""

    configured = os.environ.get("FINAHINKING_DB")
    if configured:
        return configured
    data_dir = Path(os.environ.get("FINAHINKING_DATA_DIR", Path.home() / ".finahinking"))
    return str(data_dir / "finahinking.sqlite3")

_EVENT = {
    "id": "sample-cpi-2026-01",
    "title": "CPI sample release: from event to explanation",
    "publisher": "U.S. Bureau of Labor Statistics",
    "status": "CAPTURED",
    "data_mode": "SAMPLE",
    "source_url": "https://www.bls.gov/news.release/cpi.nr0.htm",
    "chain": ["CPI", "Inflation", "Rates", "Bonds", "Discount", "Valuation"],
    "limitations": ["Deterministic fixture; not a live market feed.", "No forecast or trade instruction."],
}


@dataclass(frozen=True)
class LocalAppConfig:
    """Runtime settings.  SQLite and sample/offline mode are the defaults."""

    db_path: str = field(default_factory=default_db_path)
    host: str = "127.0.0.1"
    port: int = 8765
    sample_mode: bool = True
    offline: bool = True
    principal_id: str = "local-user"
    session_id: str = "local-session"

    def __post_init__(self) -> None:
        host = self.host.strip().lower().strip("[]")
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Finahinking local API only binds to loopback addresses")

    @classmethod
    def from_env(cls) -> LocalAppConfig:
        return cls(
            db_path=default_db_path(),
            host=os.environ.get("FINAHINKING_HOST", "127.0.0.1"),
            port=int(os.environ.get("FINAHINKING_PORT", "8765")),
            sample_mode=os.environ.get("FINAHINKING_SAMPLE", "1") not in {"0", "false"},
            offline=os.environ.get("FINAHINKING_OFFLINE", "1") not in {"0", "false"},
        )


class LocalApplication:
    """Route local product journeys through one P7-backed persistence boundary."""

    def __init__(self, config: LocalAppConfig | None = None, *, connection: sqlite3.Connection | None = None) -> None:
        self.config = config or LocalAppConfig.from_env()
        if self.config.db_path != ":memory:":
            Path(self.config.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.connection = connection or sqlite3.connect(self.config.db_path, check_same_thread=False)
        apply_p7_migration(self.connection)
        self.repository = SQLiteP7Repository(self.connection)
        self._bootstrap_identity()
        self._lock = threading.RLock()
        self._event_journey: Any | None = None
        if self.config.db_path == ":memory:":
            self.artifact_root = Path(tempfile.mkdtemp(prefix="finahinking-artifacts-"))
        else:
            self.artifact_root = Path(self.config.db_path).expanduser().parent / "artifacts"
            self.artifact_root.mkdir(parents=True, exist_ok=True)

    @property
    def csrf_token(self) -> str:
        return hashlib.sha256(f"{self.config.session_id}:finahinking-local-form".encode()).hexdigest()

    def _bootstrap_identity(self) -> None:
        principal = self.connection.execute(
            "SELECT principal_id FROM p7_principals WHERE principal_id = ?", (self.config.principal_id,)
        ).fetchone()
        if principal is None:
            self.repository.create_principal(Principal(self.config.principal_id, "Local researcher"))
        session = self.connection.execute(
            "SELECT session_id FROM p7_sessions WHERE session_id = ?", (self.config.session_id,)
        ).fetchone()
        if session is None:
            self.repository.create_session(self.config.session_id, self.config.principal_id)
        room = self.connection.execute("SELECT room_id FROM p7_rooms WHERE room_id = 'local-room'").fetchone()
        if room is None:
            self.repository.create_room(self.config.session_id, CommunityRoom("local-room", "Local evidence room", "Private local discussion", "local"))

    @staticmethod
    def _concepts(query: str = "") -> list[dict[str, Any]]:
        query = query.strip().lower()
        concepts = DEFAULT_CATALOG.search(query) if query else DEFAULT_CATALOG.concepts
        result: list[dict[str, Any]] = []
        for item in concepts:
            payload = item.to_dict()
            payload["id"] = payload["concept_id"]
            payload["definition"] = payload["formal_definition"]
            payload["equation"] = payload["equations"][0]["expression"]
            payload["source_state"] = "CURATED"
            payload["data_mode"] = "SAMPLE"
            result.append(payload)
        return result

    def knowledge(self, query: str = "") -> dict[str, Any]:
        concepts = self._concepts(query)
        paths = [item.to_dict() for item in DEFAULT_CATALOG.learning_paths]
        levels = ["intuition", "formal", "equation", "derivation", "code", "finance", "quant", "current context"]
        fingerprint = DEFAULT_CATALOG.fingerprint
        needle = query.strip().lower()
        event_matches = []
        if not needle or any(needle in str(self.event().get(field, "")).lower() for field in ("id", "title", "publisher")):
            event_matches.append({"id": self.event()["id"], "title": self.event()["title"], "source_state": self.event()["source_state"], "data_mode": self.event()["data_mode"]})
        personal = self.personal()
        research_matches = [node for node in personal.get("nodes", []) if node.get("node_type") in {"quant_run", "strategy", "paper_run"} and (not needle or needle in str(node).lower())]
        return {
            "query": query,
            "concepts": concepts,
            "learning_paths": paths,
            "learning_path": [item["id"] for item in self._concepts()],
            "levels": levels,
            "catalog_fingerprint": fingerprint,
            "provenance": "SAMPLE: curated deterministic curriculum; verify SourceReference before reuse.",
            "events": event_matches,
            "research": research_matches,
            "strategies": [node for node in research_matches if node.get("node_type") == "strategy"],
        }

    def concept(self, concept_id: str) -> dict[str, Any] | None:
        try:
            item = DEFAULT_CATALOG.get(concept_id)
        except KeyError:
            return None
        result = item.to_dict()
        result["id"] = result["concept_id"]
        result["definition"] = result["formal_definition"]
        result["equation"] = result["equations"][0]["expression"]
        result["source_state"] = "CURATED"
        result["data_mode"] = "SAMPLE"
        result.update(
            {
                "derivation": [item["statement"] for item in result["derivations"]],
                "code_example": result["code_examples"][0]["code"],
                "finance_interpretation": result["financial_interpretations"][0]["description"],
                "quant_application": result["quant_applications"][0]["description"],
                "strategy_application": result["strategy_applications"][0]["description"],
            }
        )
        return result

    def event(self) -> dict[str, Any]:
        """Replay the admitted BLS fixture when P6.5 is available.

        The compact response is intentionally a projection of the existing
        P6.5 journey, rather than a second event implementation.  A fallback
        keeps the shell importable in a minimal source checkout.
        """

        if self._event_journey is None:
            from finahinking.p6_5.bls import BLSClient
            from finahinking.p6_5.models import SourceRelease
            from finahinking.p6_5.product import UnderstandingEngine
            try:
                from finahinking.resources import fixture_path
                fixture = fixture_path("p6_5/bls_cpi_2024_2025.json")
            except ImportError:
                fixture = Path(__file__).resolve().parents[2] / "fixtures" / "p6_5" / "bls_cpi_2024_2025.json"
            captured = BLSClient.replay(
                fixture,
                capture_id="local-cpi-capture",
                retrieved_at="2025-01-15T13:32:00Z",
                first_observed_at="2025-01-15T13:31:00Z",
            )
            release = SourceRelease(
                "local-cpi-release", "bls", "bls-cpi-v2", "MACRO_RELEASE", "2024-12",
                "2025-01-15T08:30:00-05:00", "2025-01-15T13:30:00Z",
                "https://www.bls.gov/news.release/archives/cpi_01152025.htm",
            )
            self._event_journey = UnderstandingEngine(
                artifact_root=Path(tempfile.mkdtemp(prefix="finahinking-local-"))
            ).run_cpi_journey(self.config.principal_id, captured, release)
        journey = self._event_journey.to_dict()
        event = journey["event"]
        return {
            **journey,
            "id": event["event_id"],
            "title": "CPI sample release: from event to explanation",
            "publisher": "U.S. Bureau of Labor Statistics",
            "status": "CAPTURED",
            "source_state": "CAPTURED",
            "data_mode": "SAMPLE",
            "source_url": "https://www.bls.gov/news.release/archives/cpi_01152025.htm",
            "chain": ["CPI", "Inflation", "Rates", "Bonds", "Discount", "Valuation"],
            "evidence_ids": [item["evidence_id"] for item in journey.get("evidence", [])],
            "quant_status": journey.get("quant_evidence", {}).get("status", "SUCCEEDED"),
            "limitations": ["Deterministic BLS fixture; not a live market feed.", "No forecast or trade instruction."],
        }

    def diagnostics(self) -> dict[str, Any]:
        tables = [str(row["name"]) for row in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {
            "backend": "stdlib-http.server",
            "database": "sqlite",
            "database_path": "redacted; user-local app data",
            "database_filename": Path(self.config.db_path).name,
            "sample_mode": self.config.sample_mode,
            "offline": self.config.offline,
            "network": "disabled by default; no provider call is made by sample journeys",
            "secrets": "no API key configured; credentials are never logged",
            "quant_runtime": "numpy/pandas OLS and P6.6 paper-only engines available",
            "knowledge_state": {"catalog_fingerprint": DEFAULT_CATALOG.fingerprint, "concept_count": len(DEFAULT_CATALOG.concepts)},
            "source_connectivity": "offline fixture only; no provider call attempted",
            "action": "If a run fails, inspect the structured error and verify the local database is writable; no credentials are required for sample mode.",
            "tables": tables,
            "real_money_execution": False,
            "status": "ok",
        }

    def personal(self) -> dict[str, Any]:
        with self._lock:
            return self.repository.export_personal(self.config.session_id)

    def save_personal(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title", "")).strip()
        if not title or len(title) > 256:
            raise ValueError("title is required and must be at most 256 characters")
        node_type = str(payload.get("node_type", "note"))
        body = payload.get("payload", {})
        if not isinstance(body, dict):
            raise TypeError("payload must be a JSON object")
        if node_type == "learning_card":
            concept_id = str(payload.get("concept_id", "")).strip()
            outcome = str(payload.get("outcome", "neutral")).strip()
            if concept_id not in {item.concept_id for item in DEFAULT_CATALOG.concepts}:
                raise ValueError("concept_id is not in the structured knowledge catalog")
            if outcome not in {"correct", "incorrect", "neutral", "corrected"}:
                raise ValueError("outcome is invalid")
            node_id = concept_id
            node = PersonalNode(node_id, "concept", DEFAULT_CATALOG.get(concept_id).title, {"concept_id": concept_id, "source": "p7_5_catalog", "source_fingerprint": DEFAULT_CATALOG.fingerprint})
            with self._lock:
                try:
                    self.repository.get_node(self.config.session_id, node_id)
                except KeyError:
                    self.repository.save_node(self.config.session_id, node)
                evidence = MasteryEvidence(f"mastery:{concept_id}:{uuid.uuid4().hex}", node_id, "quiz_response", f"knowledge:{concept_id}:self-check", outcome, "2026-10-03T00:00:00Z", {"response": str(payload.get("outcome"))})
                self.repository.save_mastery_evidence(self.config.session_id, evidence)
            return {"node_id": node_id, "node_type": "concept", "concept_id": concept_id, "outcome": outcome, "saved": True}
        node = PersonalNode(f"local-{uuid.uuid4().hex}", node_type, title, dict(body))
        with self._lock:
            self.repository.save_node(self.config.session_id, node)
        return {"node_id": node.node_id, "title": node.title, "node_type": node.node_type, "saved": True}

    def route(self, method: str, path: str, *, query: Mapping[str, list[str]] | None = None, body: Any = None) -> tuple[int, str, Any]:
        """Return ``(status, content_type, payload)`` without requiring a socket."""

        parsed = urlsplit(path)
        query = parse_qs(parsed.query) if query is None else query
        clean = parsed.path.rstrip("/") or "/"
        if clean in {"/health", "/api/health"}:
            return 200, "application/json", {"status": "ok", "service": "finahinking-local", "version": "0.1.0"}
        if clean == "/api/diagnostics":
            return 200, "application/json", self.diagnostics()
        if clean in {"/api/knowledge", "/knowledge.json"}:
            return 200, "application/json", self.knowledge((query.get("q") or [""])[0])
        if clean.startswith("/api/concepts/"):
            if clean.endswith("/prerequisites"):
                concept_id = clean.removeprefix("/api/concepts/").removesuffix("/prerequisites").strip("/")
                try:
                    closure = DEFAULT_CATALOG.prerequisite_closure(concept_id)
                except KeyError:
                    return 404, "application/json", {"error": "concept not found"}
                return 200, "application/json", {"concept_id": concept_id, "concepts": [item.to_dict() for item in closure]}
            concept = self.concept(clean.removeprefix("/api/concepts/"))
            return (200, "application/json", concept) if concept else (404, "application/json", {"error": "concept not found"})
        if clean.startswith("/api/knowledge/path/"):
            path_id = clean.removeprefix("/api/knowledge/path/")
            try:
                return 200, "application/json", DEFAULT_CATALOG.path(path_id).to_dict()
            except KeyError:
                return 404, "application/json", {"error": "learning path not found"}
        if clean == "/api/events":
            return 200, "application/json", {"events": [self.event()]}
        if clean in {"/api/events/save", "/api/events/learn"} and method == "POST":
            journey = self._event_journey
            if journey is None:
                self.event()
                journey = self._event_journey
            assert journey is not None
            event_id = journey.event.event_id
            with self._lock:
                try:
                    existing = self.repository.get_node(self.config.session_id, f"event:{event_id}")
                    return 201, "application/json", {"saved": True, "event_id": event_id, "node_id": existing.node_id, "node_type": existing.node_type, "title": existing.title}
                except KeyError:
                    result = EventLearningAdapter(self.repository).ingest_journey(self.config.session_id, journey)
            return 201, "application/json", {"saved": True, "event_id": result.event_id, "node_id": result.event_node_id, "node_type": "event", "history_id": result.history_id}
        if clean == "/api/quant":
            if method != "POST":
                return 200, "application/json", {"stage": "experiment", "question": "How does the market relate to asset returns?", "hypothesis": "Market returns have a measurable historical beta to asset returns.", "execution": "POST required to create a private ResearchRun", "real_money": False}
            from finahinking.p7_5.research import LocalResearchService
            try:
                result = LocalResearchService(self.repository, self.config.session_id, self.artifact_root).run_quant(dict(body or {}) if method == "POST" else {})
            except (TypeError, ValueError, PermissionError) as exc:
                return 400, "application/json", {"error": str(exc), "action": "revise the bounded research question/options"}
            numeric = dict(result.get("numeric_results", {}))
            numeric.setdefault("observations", numeric.get("sample_count"))
            numeric.setdefault("slope", numeric.get("beta"))
            return 200, "application/json", {**result, "stage": "result" if method == "POST" else "experiment", "question": (body or {}).get("question", "How does the market relate to asset returns?") if isinstance(body, Mapping) else "How does the market relate to asset returns?", "hypothesis": (body or {}).get("hypothesis", "Market returns have a measurable historical beta to asset returns.") if isinstance(body, Mapping) else "Market returns have a measurable historical beta to asset returns.", "result": numeric}
        if clean == "/api/strategy":
            if method != "POST":
                return 200, "application/json", {"stages": ["idea", "spec", "features", "code", "backtest", "oos", "paper", "compare", "learn"], "execution": "paper-only", "real_money": False}
            from finahinking.p7_5.research import LocalResearchService
            try:
                result = LocalResearchService(self.repository, self.config.session_id, self.artifact_root).run_strategy(dict(body or {}))
            except (TypeError, ValueError, PermissionError) as exc:
                return 400, "application/json", {"error": str(exc), "action": "choose a supported reviewed strategy template"}
            return 200, "application/json", {**result, "strategy_spec": result.get("strategy"), "real_money": False, "execution": "paper-only", "backtest": {**dict(result.get("backtest") or {}), "metrics": result.get("numeric_results", {})}, "oos": {**dict(result.get("oos") or {}), "metrics": result.get("numeric_results", {})}, "paper": {**dict(result.get("paper") or {}), "status": "PAPER_ONLY"}}
        if clean.startswith("/api/research/artifacts/"):
            node_id = clean.removeprefix("/api/research/artifacts/").strip("/")
            if not node_id or any(part in node_id for part in ("/", "\\", "..")):
                return 400, "application/json", {"error": "artifact id is invalid"}
            from finahinking.p7_5.research import LocalResearchService
            try:
                artifact = LocalResearchService(self.repository, self.config.session_id, self.artifact_root).get_artifact(node_id)
            except (KeyError, ValueError, PermissionError) as exc:
                return 404, "application/json", {"error": str(exc), "action": "run or save the research artifact first"}
            return 200, "application/json", artifact
        if clean == "/api/personal":
            return 200, "application/json", self.personal()
        if clean == "/api/community":
            if method == "POST":
                values = dict(body or {}) if isinstance(body, Mapping) else {}
                text = str(values.get("claim", "")).strip()
                if not text:
                    return 400, "application/json", {"error": "claim is required"}
                post_id = f"post:{uuid.uuid4().hex}"
                post = CommunityPost(post_id, "local-room", self.config.principal_id, "HYPOTHESIS", "Private research question", text)
                claim = CommunityClaim(f"claim:{post_id}", post_id, "HYPOTHESIS", text)
                CommunityIntegrityService(self.repository).create_post(self.config.session_id, post, claim, available_evidence=())
                return 201, "application/json", {"saved": True, "post_id": post_id, "visibility": "PRIVATE", "projection_required": True}
            rows = self.connection.execute("SELECT post_id,room_id,author_id,claim_type,title,body,status,created_at FROM p7_posts WHERE room_id = ? ORDER BY created_at DESC", ("local-room",)).fetchall()
            posts = [{**dict(row), "evidence_ids": []} for row in rows]
            return 200, "application/json", {"posts": posts, "model": "calm evidence discussion", "leaderboards": False, "private_by_default": True, "projection_required": True}
        if clean == "/api/community/project" and method == "POST":
            values = dict(body or {}) if isinstance(body, Mapping) else {}
            if str(values.get("consent", "")).lower() not in {"1", "true", "yes", "on"}:
                return 403, "application/json", {"error": "explicit projection consent is required", "action": "review the allow-listed fields and consent"}
            if self._event_journey is None:
                self.event()
            event_id = str(values.get("source_id", self._event_journey.event.event_id))
            if not event_id:
                return 400, "application/json", {"error": "source_id is required"}
            try:
                event_payload = self.event()
                source_fingerprint = self._event_journey.event.fingerprint
                self.repository.get_node(self.config.session_id, f"event:{event_id}")
            except (KeyError, AttributeError):
                return 404, "application/json", {"error": "save the research source privately before projecting it"}
            fields = tuple(item.strip() for item in str(values.get("fields", "event_type,reference_period,published_at,revision_status,limitations")).split(",") if item.strip())
            allowed = {"event_type", "reference_period", "published_at", "revision_status", "limitations"}
            if not fields or any(item not in allowed for item in fields):
                return 400, "application/json", {"error": "fields must be an explicit allow-list", "allowed_fields": sorted(allowed)}
            spec = ProjectionSpec(f"projection:{uuid.uuid4().hex}", "p6_5_event", event_id, source_fingerprint, fields, str(values.get("visibility", "PUBLIC")).upper(), 1, ("Descriptive projection only; source evidence and limitations remain attached.",), None)
            try:
                projection_payload = {**dict(event_payload.get("event", {})), "limitations": event_payload.get("limitations", [])}
                projection = self.repository.publish_projection(self.config.session_id, spec, projection_payload, consent=True)
            except (PermissionError, ValueError) as exc:
                return 400, "application/json", {"error": str(exc), "action": "check saved source, visibility, and allow-listed fields"}
            return 201, "application/json", {"projection_id": projection.projection_id, "visibility": projection.visibility, "fields": list(fields), "consented": True, "limitations": list(projection.limitations)}
        if clean == "/api/personal/save" and method == "POST":
            try:
                return 201, "application/json", self.save_personal(body if isinstance(body, dict) else {})
            except (TypeError, ValueError) as exc:
                return 400, "application/json", {"error": str(exc)}
        if clean == "/api/reopen" and method == "POST":
            return 200, "application/json", {"reopened": True, "personal": self.personal()}
        if clean.startswith("/knowledge/"):
            concept = self.concept(clean.removeprefix("/knowledge/"))
            if concept is None:
                return 404, "text/html; charset=utf-8", "<h1>Concept not found</h1>"
            return 200, "text/html; charset=utf-8", self.render_concept_page(concept)
        if clean in {"/", "/events", "/knowledge", "/quant", "/strategy", "/personal", "/community", "/diagnostics"}:
            return 200, "text/html; charset=utf-8", self.render_page(clean)
        return 404, "application/json", {"error": "route not found"}

    def render_page(self, page: str) -> str:
        names = {
            "/": "Home",
            "/events": "Events",
            "/knowledge": "Knowledge",
            "/quant": "Quant lab",
            "/strategy": "Strategy lab",
            "/personal": "Personal",
            "/community": "Community",
            "/diagnostics": "Diagnostics",
        }
        title = names.get(page, "Finahinking")
        body = self._page_body(page)
        links = " ".join(f'<a href="{href}">{html.escape(label)}</a>' for href, label in names.items())
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{html.escape(title)} · Finahinking</title>"
            '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; style-src \'unsafe-inline\'; script-src \'none\'; connect-src \'self\'">'
            '<style>body{font:16px system-ui,sans-serif;max-width:980px;margin:0 auto;padding:24px;color:#182026;background:#f7f7f2}nav{display:flex;gap:12px;flex-wrap:wrap;padding:12px 0;border-bottom:1px solid #ccd2ce}a{color:#095a66}main{padding:20px 0}article{background:white;border:1px solid #d8dfdb;border-radius:10px;padding:16px;margin:12px 0}code{background:#eef2ef;padding:2px 4px}ul{line-height:1.7}.badge{font-size:.8em;letter-spacing:.08em;background:#e4efe9;padding:4px 7px;border-radius:6px}</style></head>'
            f'<body><a href="#main">Skip to content</a><nav aria-label="Primary">{links}</nav><main id="main"><p class="badge">LOCAL · {"SAMPLE" if self.config.sample_mode else "LIVE"} · {"OFFLINE" if self.config.offline else "NETWORK ENABLED"}</p>{body}</main></body></html>'
        )

    @staticmethod
    def render_result_page(title: str, payload: Any) -> str:
        escaped = html.escape(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{html.escape(title)} · Finahinking</title><style>body{{font:16px system-ui,sans-serif;max-width:980px;margin:0 auto;padding:24px;color:#182026;background:#f7f7f2}}pre{{white-space:pre-wrap;background:white;border:1px solid #d8dfdb;border-radius:10px;padding:16px;overflow:auto}}a{{color:#095a66}}</style></head>"
            f"<body><a href='/'>← Home</a><main><h1>{html.escape(title)}</h1><p>Saved result and provenance are shown below. Continue in <a href='/personal'>Personal</a> or return to the <a href='/events'>event</a>, <a href='/quant'>Quant</a>, <a href='/strategy'>Strategy</a>, or <a href='/community'>Community</a> workspace.</p><pre>{escaped}</pre></main></body></html>"
        )

    def render_concept_page(self, concept: Mapping[str, Any]) -> str:
        """Render a concept page with the same progressive disclosure contract."""

        title = html.escape(str(concept.get("title", concept.get("id", "Concept"))))
        equation = html.escape(str(concept.get("equation", "")))
        definition = html.escape(str(concept.get("definition", concept.get("formal_definition", ""))))
        prerequisites = concept.get("prerequisites", ())
        links = " ".join(f"<a href='/knowledge/{html.escape(str(item))}'>{html.escape(str(item))}</a>" for item in prerequisites)
        derivation = concept.get("derivations", [])
        code = concept.get("code_examples", [])
        finance = concept.get("financial_interpretations", [])
        quant = concept.get("quant_applications", [])
        strategy = concept.get("strategy_applications", [])
        current = html.escape(str(concept.get("current_context", "")))
        intuition = html.escape(str(concept.get("intuition", "")))
        formal = html.escape(str(concept.get("formal_definition", definition)))
        assumptions = "".join(f"<li>{html.escape(str(item))}</li>" for item in concept.get("assumptions", []))
        misconceptions = "".join(f"<li><strong>{html.escape(str(item.get('claim', '')))}</strong> — {html.escape(str(item.get('correction', '')))}</li>" for item in concept.get("misconceptions", []))
        proofs = "".join(f"<li>{html.escape(str(item.get('statement', item.get('text', '')) if isinstance(item, Mapping) else item))}</li>" for item in concept.get("proofs", []))
        sources = "".join(f"<li><a rel='noopener noreferrer' href='{html.escape(str(item.get('locator', item.get('url', '#'))))}'>{html.escape(str(item.get('title', item.get('reference_id', 'source'))))}</a> <small>{html.escape(str(item.get('kind', 'reference')))}</small></li>" for item in concept.get("source_references", []))
        derivation_html = "".join(f"<li><strong>{html.escape(str(item.get('statement', '')))}</strong> — {html.escape(str(item.get('what_changed', '')))} <em>{html.escape(str(item.get('why_valid', '')))}</em></li>" for item in derivation)
        code_html = "".join(f"<pre><code>{html.escape(str(item.get('code', '')))}</code></pre><p>{html.escape(str(item.get('input_description', '')))} {html.escape(str(item.get('output_description', '')))}</p>" for item in code)
        finance_html = "".join(f"<p><strong>{html.escape(str(item.get('title', '')))}</strong> — {html.escape(str(item.get('description', '')))}</p>" for item in finance)
        quant_html = "".join(f"<p><strong>{html.escape(str(item.get('title', '')))}</strong> — {html.escape(str(item.get('description', '')))}</p>" for item in quant)
        strategy_html = "".join(f"<p><strong>{html.escape(str(item.get('title', '')))}</strong> — {html.escape(str(item.get('description', '')))}</p>" for item in strategy)
        concept_id = html.escape(str(concept.get("id", "")))
        mastery = self.repository.get_mastery_state(self.config.session_id, str(concept.get("id", "")))
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{title} · Knowledge</title>"
            '<style>body{font:16px system-ui,sans-serif;max-width:820px;margin:0 auto;padding:24px;color:#182026;background:#f7f7f2}article{background:white;border:1px solid #d8dfdb;border-radius:10px;padding:18px;margin:12px 0}a{color:#095a66}code{background:#eef2ef;padding:3px}</style></head>'
            f"<body><a href='/knowledge'>← Knowledge index</a><main><h1>{title}</h1>"
            f"<article><h2>Intuition</h2><p>{intuition}</p></article>"
            f"<article><h2>Formal</h2><p>{formal}</p></article>"
            f"<article><h2>Equation</h2><code>{equation}</code></article>"
            f"<article><h2>Derivation</h2><ol>{derivation_html}</ol></article>"
            f"<article><h2>Code</h2>{code_html}</article>"
            f"<article><h2>Finance</h2>{finance_html}</article>"
            f"<article><h2>Quant</h2>{quant_html}</article>"
            f"<article><h2>Strategy</h2>{strategy_html}</article>"
            f"<article><h2>Current context</h2><p>{current}</p></article>"
            f"<article><h2>Personal mastery</h2><p><strong>{html.escape(mastery.state)}</strong> · {mastery.evidence_count} evidence item(s). {html.escape(mastery.explanation)}</p></article>"
            f"<article><h2>Assumptions and proof boundary</h2><ul>{assumptions or '<li>No extra assumptions recorded.</li>'}</ul><ol>{proofs}</ol></article>"
            f"<article><h2>Misconceptions</h2><ul>{misconceptions or '<li>No misconception has been recorded.</li>'}</ul></article>"
            f"<article><h2>Sources and limits</h2><ul>{sources or '<li>Source locator unavailable.</li>'}</ul></article>"
            f"<article><h2>Prerequisites</h2><p>{links or 'None'}</p></article>"
            f'<article><h2>Check your understanding</h2><form method="post" action="/api/personal/save"><input type="hidden" name="_csrf" value="{self.csrf_token}"><input type="hidden" name="node_type" value="learning_card"><input type="hidden" name="title" value="{title} self-check"><input type="hidden" name="concept_id" value="{concept_id}"><label for="outcome">What is the main caveat?</label><select id="outcome" name="outcome"><option value="correct">I can explain it with its assumptions</option><option value="incorrect">I would treat it as a guarantee</option></select><button type="submit">Save learning evidence</button></form></article>'
            f"<p>Progressive path: intuition → formal → equation → derivation → code → finance → quant → current context. <a href='/api/concepts/{concept_id}'>View structured source contract</a>.</p></main></body></html>"
        )

    def _page_body(self, page: str) -> str:
        if page == "/":
            return "<h1>Finahinking local research lab</h1><p>Follow an evidence-bound path: understand an event, learn the concept, run a quant experiment, then keep the strategy paper-only.</p><ul><li>Start with the <a href='/events'>sample CPI event</a>.</li><li>Browse the <a href='/knowledge'>structured knowledge path</a>.</li><li>Open <a href='/diagnostics'>diagnostics</a> if a local step needs attention.</li></ul><p>Real-money execution is intentionally unavailable.</p>"
        if page == "/events":
            event = self.event()
            claims = "".join(f"<li>{html.escape(str(item.get('text', item.get('claim', ''))))}</li>" for item in event.get("claims", []))
            evidence = "".join(f"<li><a href='{html.escape(str(item.get('reference', '#')))}'>{html.escape(str(item.get('evidence_id', 'evidence')))}</a>: {html.escape(str(item.get('scope', '')))}</li>" for item in event.get("evidence", []))
            return f"<h1>Events</h1><article><h2>{html.escape(event['title'])}</h2><p><span class='badge'>{event['status']}</span> <span class='badge'>{event['data_mode']}</span></p><p>{html.escape(' → '.join(event['chain']))}</p><p>Continue to <a href='/knowledge/inflation'>inflation knowledge</a>, <a href='/knowledge/beta'>beta and uncertainty</a>, or the <a href='/quant'>quant experiment</a>.</p><h3>What changed</h3><p>{html.escape(str(event.get('what_changed','')))}</p><h3>Claims</h3><ul>{claims}</ul><h3>Show evidence</h3><ul>{evidence}</ul><p>{html.escape(event['limitations'][0])}</p><form method='post' action='/api/events/learn'><input type='hidden' name='_csrf' value='{self.csrf_token}'><button type='submit'>Save this private learning thread</button></form></article>"
        if page == "/knowledge":
            cards = "".join(f"<article><h2><a href='/knowledge/{item['id']}'>{html.escape(item['title'])}</a></h2><p>{html.escape(item['definition'])}</p><p><code>{html.escape(item['equation'])}</code></p><p>Prerequisites: {html.escape(', '.join(item['prerequisites']) or 'none')}</p></article>" for item in self._concepts())
            return f"<h1>Knowledge</h1><p>Progressive levels: intuition → formal → equation → derivation → code → finance → quant.</p>{cards}"
        if page == "/quant":
            return f"<h1>Quant lab</h1><article><h2>Question → hypothesis → experiment → result → evidence</h2><form method='post' action='/api/quant'><input type='hidden' name='_csrf' value='{self.csrf_token}'><label for='question'>Research question</label><input id='question' name='question' value='Does beta explain the sample?'><button type='submit'>Run deterministic experiment</button></form><p>Results carry a fixture fingerprint, uncertainty, and limitations. A run is descriptive research, not a trading instruction.</p><span class='badge'>SAMPLE</span></article>"
        if page == "/strategy":
            return f"<h1>Strategy lab</h1><article><h2>One StrategySpec, multiple review stages</h2><form method='post' action='/api/strategy'><input type='hidden' name='_csrf' value='{self.csrf_token}'><label for='idea'>Strategy idea</label><input id='idea' name='idea' value='Long recent winners'><button type='submit'>Review and run paper research</button></form><p>Idea → spec → features → code → backtest → out-of-sample → paper → compare → learn → export.</p><p><strong>Paper-only:</strong> broker connections and real-money orders are not implemented.</p></article>"
        if page == "/personal":
            personal = self.personal()
            return f"<h1>Personal continuity</h1><p>Private graph for <code>{html.escape(self.config.principal_id)}</code>. Saved nodes: {len(personal.get('nodes', []))}; histories: {len(personal.get('history', []))}.</p><form method=\"post\" action=\"/api/personal/save\"><input type=\"hidden\" name=\"_csrf\" value=\"{self.csrf_token}\"><input type=\"hidden\" name=\"node_type\" value=\"note\"><label for=\"note-title\">Save a note</label><input id=\"note-title\" name=\"title\"><button type=\"submit\">Save privately</button></form><p>Reopen this page after restart to continue where you stopped.</p>"
        if page == "/community":
            community = self.route("GET", "/api/community")[2]
            posts = "".join(f"<article><h3>{html.escape(str(item.get('title','')))}</h3><p>{html.escape(str(item.get('body','')))}</p><small>{html.escape(str(item.get('claim_type','')))} · evidence: {html.escape(', '.join(item.get('evidence_ids', [])))}</small></article>" for item in community.get("posts", []))
            event_id = html.escape(str(self.event().get("id", "")))
            return f"<h1>Community</h1><article><h2>Calm evidence discussion</h2><p>Claims, evidence, research runs, questions, and counter-evidence are visible only through explicit projection. Nothing private is shared without explicit projection consent. There are no leaderboards or hype rankings.</p><form method='post' action='/api/community'><input type='hidden' name='_csrf' value='{self.csrf_token}'><label for='claim'>Claim or question</label><textarea id='claim' name='claim'></textarea><button type='submit'>Save private question</button></form><form method='post' action='/api/community/project'><input type='hidden' name='_csrf' value='{self.csrf_token}'><input type='hidden' name='source_id' value='{event_id}'><input type='hidden' name='fields' value='event_type,reference_period,published_at,revision_status,limitations'><label><input type='checkbox' name='consent' value='true'> I consent to this explicit descriptive projection</label><button type='submit'>Project selected event fields</button></form><span class='badge'>PRIVATE BY DEFAULT</span></article>{posts}"
        return "<h1>Diagnostics</h1><pre>" + html.escape(json.dumps(self.diagnostics(), indent=2, sort_keys=True)) + "</pre>"

    def close(self) -> None:
        self.connection.close()


class _Handler(BaseHTTPRequestHandler):
    server_version = "FinahinkingLocal/0.1"

    def _application(self) -> LocalApplication:
        return self.server.application

    def _send(self, status: int, content_type: str, payload: Any) -> None:
        raw = payload.encode("utf-8") if isinstance(payload, str) else json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'none'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("Set-Cookie", "finahinking_session=local; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(raw)

    def _safe_origin(self) -> bool:
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]").lower()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            return False
        origin = self.headers.get("Origin")
        if origin:
            parsed_origin = urlsplit(origin)
            origin_host = (parsed_origin.hostname or "").strip("[]").lower()
            if parsed_origin.scheme not in {"http", "https"} or origin_host not in {"127.0.0.1", "localhost", "::1"}:
                return False
        return True

    def do_GET(self) -> None:
        if not self._safe_origin():
            self._send(403, "application/json", {"error": "loopback origin required"})
            return
        parsed = urlsplit(self.path)
        try:
            status, content_type, payload = self._application().route("GET", parsed.path, query=parse_qs(parsed.query))
            self._send(status, content_type, payload)
        except (AttributeError, KeyError, ValueError, TypeError, RuntimeError) as exc:
            self._send(503, "application/json", {"error": str(exc), "action": "inspect /diagnostics and retry"})

    def do_POST(self) -> None:
        if not self._safe_origin():
            self._send(403, "application/json", {"error": "loopback origin required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send(400, "application/json", {"error": "invalid content length"})
            return
        if length < 0:
            self._send(400, "application/json", {"error": "invalid content length"})
            return
        if length > 1_000_000:
            self._send(413, "application/json", {"error": "request body too large"})
            return
        raw = self.rfile.read(length)
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].lower()
        if content_type == "application/x-www-form-urlencoded":
            values = parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True)
            token = (values.pop("_csrf", [""]) or [""])[0]
            if token != self._application().csrf_token:
                self._send(403, "application/json", {"error": "csrf token is required"})
                return
            body = {key: (items[-1] if len(items) == 1 else items) for key, items in values.items()}
        else:
            try:
                body = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                self._send(400, "application/json", {"error": "request body must be JSON or a protected form"})
                return
        parsed = urlsplit(self.path)
        try:
            status, response_type, payload = self._application().route("POST", parsed.path, body=body)
            if content_type == "application/x-www-form-urlencoded" and response_type == "application/json":
                self._send(status, "text/html; charset=utf-8", self._application().render_result_page("Research result", payload))
            else:
                self._send(status, response_type, payload)
        except (AttributeError, KeyError, ValueError, TypeError, RuntimeError, PermissionError) as exc:
            self._send(400, "application/json", {"error": str(exc), "action": "inspect /diagnostics and retry"})

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def create_server(application: LocalApplication | None = None, *, host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    """Create a server without starting it (useful for smoke/E2E tests)."""

    app = application or LocalApplication()
    resolved_host = host or app.config.host
    if resolved_host.strip().lower().strip("[]") not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Finahinking local API only binds to loopback addresses")
    address = (resolved_host, int(port if port is not None else app.config.port))
    server = ThreadingHTTPServer(address, _Handler)
    server.application = app  # type: ignore[attr-defined]
    return server


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the Finahinking local-first sample application")
    parser.add_argument("--host", default=None, help="loopback host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="TCP port (default: 8765)")
    parser.add_argument("--db", default=None, help="SQLite path (default: user-local persistent file)")
    parser.add_argument("--sample", action="store_true", help="enable deterministic sample mode")
    parser.add_argument("--offline", action="store_true", help="disable outbound providers")
    parser.add_argument("--smoke", action="store_true", help="check health and sample routes, then exit")
    args = parser.parse_args(argv)
    base = LocalAppConfig.from_env()
    config = LocalAppConfig(
        db_path=args.db or base.db_path,
        host=args.host or base.host,
        port=args.port if args.port is not None else base.port,
        sample_mode=True if args.sample else base.sample_mode,
        offline=True if args.offline else base.offline,
        principal_id=base.principal_id,
        session_id=base.session_id,
    )
    app = LocalApplication(config)
    if args.smoke:
        health = app.route("GET", "/api/health")
        events = app.route("GET", "/api/events")
        knowledge = app.route("GET", "/api/knowledge")
        if health[0] != 200 or events[0] != 200 or knowledge[0] != 200:
            app.close()
            raise SystemExit("local sample smoke failed")
        print("local sample smoke passed")
        app.close()
        return
    server = create_server(app)
    print(f"Finahinking local app listening on http://{server.server_address[0]}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        app.close()


__all__ = ["LocalAppConfig", "LocalApplication", "create_server", "main"]
