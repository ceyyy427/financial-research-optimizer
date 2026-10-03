"""Small, offline-first local application shell for Finahinking.

The shell deliberately contains no domain logic or provider credentials.  It
adapts the existing P7 repository and exposes deterministic HTML/JSON routes
for the event, knowledge, quant, strategy, personal, and community journeys.
The same object can be mounted in the stdlib HTTP server or exercised directly
by tests, which keeps the local runtime inspectable and inexpensive to run.
"""

from __future__ import annotations

import argparse
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

from finahinking.p7 import PersonalNode, Principal, SQLiteP7Repository, apply_p7_migration
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
        return {
            "query": query,
            "concepts": concepts,
            "learning_paths": paths,
            "learning_path": [item["id"] for item in self._concepts()],
            "levels": levels,
            "catalog_fingerprint": fingerprint,
            "provenance": "SAMPLE: curated deterministic curriculum; verify SourceReference before reuse.",
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
            try:
                from finahinking.p6_5.bls import BLSClient
                from finahinking.p6_5.models import SourceRelease
                from finahinking.p6_5.product import UnderstandingEngine

                fixture = Path(__file__).resolve().parents[2] / "fixtures" / "p6_5" / "bls_cpi_2024_2025.json"
                captured = BLSClient.replay(
                    fixture,
                    capture_id="local-cpi-capture",
                    retrieved_at="2025-01-15T13:32:00Z",
                    first_observed_at="2025-01-15T13:31:00Z",
                )
                release = SourceRelease(
                    "local-cpi-release",
                    "bls",
                    "bls-cpi-v2",
                    "MACRO_RELEASE",
                    "2024-12",
                    "2025-01-15T08:30:00-05:00",
                    "2025-01-15T13:30:00Z",
                    "https://www.bls.gov/news.release/archives/cpi_01152025.htm",
                )
                self._event_journey = UnderstandingEngine(
                    artifact_root=Path(tempfile.mkdtemp(prefix="finahinking-local-"))
                ).run_cpi_journey("local-user", captured, release)
            except (ImportError, OSError, TypeError, ValueError, RuntimeError):
                self._event_journey = False
        if self._event_journey:
            journey = self._event_journey.to_dict()
            event = journey["event"]
            return {
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
        return dict(_EVENT)

    def diagnostics(self) -> dict[str, Any]:
        tables = [str(row["name"]) for row in self.connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {
            "backend": "stdlib-http.server",
            "database": "sqlite",
            "database_path": self.config.db_path,
            "sample_mode": self.config.sample_mode,
            "offline": self.config.offline,
            "network": "disabled by default; no provider call is made by sample journeys",
            "secrets": "no API key configured; credentials are never logged",
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
            event = self.event()
            return 201, "application/json", self.save_personal(
                {"title": event["title"], "node_type": "event", "payload": event}
            )
        if clean == "/api/quant":
            event = self.event()
            return 200, "application/json", {"stage": "experiment", "question": "Does volatility change across the sample window?", "hypothesis": "Rolling volatility is a descriptive feature, not a forecast.", "result": {"status": event.get("quant_status", "SAMPLE"), "source_state": "CAPTURED", "evidence": event.get("evidence_ids", ["QUANT-FIXTURE-001"])[-1]}}
        if clean == "/api/strategy":
            return 200, "application/json", {"stages": ["idea", "spec", "features", "backtest", "oos", "paper", "compare", "learn"], "execution": "paper-only", "real_money": False}
        if clean == "/api/personal":
            return 200, "application/json", self.personal()
        if clean == "/api/community":
            return 200, "application/json", {"posts": [], "model": "calm evidence discussion", "leaderboards": False, "private_by_default": True}
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

    def render_concept_page(self, concept: Mapping[str, Any]) -> str:
        """Render a concept page with the same progressive disclosure contract."""

        title = html.escape(str(concept.get("title", concept.get("id", "Concept"))))
        equation = html.escape(str(concept.get("equation", "")))
        definition = html.escape(str(concept.get("definition", concept.get("formal_definition", ""))))
        prerequisites = concept.get("prerequisites", ())
        links = " ".join(f"<a href='/knowledge/{html.escape(str(item))}'>{html.escape(str(item))}</a>" for item in prerequisites)
        return (
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{title} · Knowledge</title>"
            '<style>body{font:16px system-ui,sans-serif;max-width:820px;margin:0 auto;padding:24px;color:#182026;background:#f7f7f2}article{background:white;border:1px solid #d8dfdb;border-radius:10px;padding:18px;margin:12px 0}a{color:#095a66}code{background:#eef2ef;padding:3px}</style></head>'
            f"<body><a href='/knowledge'>← Knowledge index</a><main><h1>{title}</h1><p>{definition}</p><article><h2>Equation</h2><code>{equation}</code></article><article><h2>Prerequisites</h2><p>{links or 'None'}</p></article><article><h2>Derivation and applications</h2><p>Progressive levels: intuition → formal → equation → derivation → code → finance → quant → current context.</p><p>Inspect the JSON contract at <a href='/api/concepts/{html.escape(str(concept.get('id', '')))}'>concept API</a>.</p></article></main></body></html>"
        )

    def _page_body(self, page: str) -> str:
        if page == "/":
            return "<h1>Finahinking local research lab</h1><p>Follow an evidence-bound path: understand an event, learn the concept, run a quant experiment, then keep the strategy paper-only.</p><ul><li>Start with the <a href='/events'>sample CPI event</a>.</li><li>Browse the <a href='/knowledge'>structured knowledge path</a>.</li><li>Open <a href='/diagnostics'>diagnostics</a> if a local step needs attention.</li></ul><p>Real-money execution is intentionally unavailable.</p>"
        if page == "/events":
            event = self.event()
            return f"<h1>Events</h1><article><h2>{html.escape(event['title'])}</h2><p><span class='badge'>{event['status']}</span> <span class='badge'>{event['data_mode']}</span></p><p>{html.escape(' → '.join(event['chain']))}</p><p>{html.escape(event['limitations'][0])}</p></article>"
        if page == "/knowledge":
            cards = "".join(f"<article><h2><a href='/knowledge/{item['id']}'>{html.escape(item['title'])}</a></h2><p>{html.escape(item['definition'])}</p><p><code>{html.escape(item['equation'])}</code></p><p>Prerequisites: {html.escape(', '.join(item['prerequisites']) or 'none')}</p></article>" for item in self._concepts())
            return f"<h1>Knowledge</h1><p>Progressive levels: intuition → formal → equation → derivation → code → finance → quant.</p>{cards}"
        if page == "/quant":
            return "<h1>Quant lab</h1><article><h2>Question → hypothesis → experiment → result → evidence</h2><p>Rolling volatility is computed only from available sample observations. Results carry a fixture fingerprint and limitations.</p><span class='badge'>SAMPLE</span></article>"
        if page == "/strategy":
            return "<h1>Strategy lab</h1><article><h2>One StrategySpec, multiple review stages</h2><p>Idea → spec → features → backtest → out-of-sample → paper → compare → learn → export.</p><p><strong>Paper-only:</strong> broker connections and real-money orders are not implemented.</p></article>"
        if page == "/personal":
            personal = self.personal()
            return f"<h1>Personal continuity</h1><p>Private graph for <code>{html.escape(self.config.principal_id)}</code>. Saved nodes: {len(personal.get('nodes', []))}; histories: {len(personal.get('history', []))}.</p><p>Reopen this page after restart to continue where you stopped.</p>"
        if page == "/community":
            return "<h1>Community</h1><article><h2>Calm evidence discussion</h2><p>Claims, evidence, research runs, questions, and counter-evidence are visible only through explicit projections. There are no leaderboards or hype rankings.</p><span class='badge'>PRIVATE BY DEFAULT</span></article>"
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
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        status, content_type, payload = self._application().route("GET", parsed.path, query=parse_qs(parsed.query))
        self._send(status, content_type, payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            self._send(413, "application/json", {"error": "request body too large"})
            return
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, "application/json", {"error": "request body must be JSON"})
            return
        parsed = urlsplit(self.path)
        status, content_type, payload = self._application().route("POST", parsed.path, body=body)
        self._send(status, content_type, payload)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def create_server(application: LocalApplication | None = None, *, host: str | None = None, port: int | None = None) -> ThreadingHTTPServer:
    """Create a server without starting it (useful for smoke/E2E tests)."""

    app = application or LocalApplication()
    address = (host or app.config.host, int(port if port is not None else app.config.port))
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
