from __future__ import annotations

import sqlite3

from finahinking.local_app import LocalAppConfig, LocalApplication


def _app() -> LocalApplication:
    return LocalApplication(LocalAppConfig(db_path=":memory:", offline=True, session_id="p82b-ui", principal_id="p82b-ui"), connection=sqlite3.connect(":memory:"))


def test_knowledge_api_exposes_mathml_references_and_no_context_state() -> None:
    app = _app()
    status, content_type, payload = app.route("GET", "/api/p8_2b/knowledge/ols")
    assert status == 200 and content_type == "application/json"
    assert payload["schema_version"] == 1
    assert payload["unit"]["unit_id"] == "ols"
    assert "mathml" in payload["unit"]["equations"][0]
    assert payload["context"]["status"] == "NO_CONTEXT_AVAILABLE"
    assert payload["references"][0]["reference_id"] == "ols-1922"


def test_context_route_and_html_use_server_owned_values_and_no_js_fallback() -> None:
    app = _app()
    status, _, payload = app.route("GET", "/api/p8_2b/knowledge/volatility/context", query={"context_type": ["research_point"], "context_id": ["DEMO-20260103T000000Z"]})
    assert status == 200
    assert payload["status"] == "AVAILABLE"
    assert payload["binding"]["dataset_fingerprint"]
    status, _, html = app.route("GET", "/knowledge/ols")
    assert status == 200
    assert 'data-finathink-knowledge' in html
    assert 'data-knowledge-equation="ols-line"' in html
    assert "MathML" in html
    assert "Teach me this" in html


def test_widget_route_is_typed_and_rejects_unknown_kind() -> None:
    app = _app()
    status, _, payload = app.route("POST", "/api/p8_2b/widgets", body={"widget_id": "v1", "kind": "volatility", "parameters": {"returns": [0.01, -0.01]}})
    assert status == 200 and payload["status"] == "PASS"
    status, _, payload = app.route("POST", "/api/p8_2b/widgets", body={"widget_id": "x", "kind": "python", "parameters": {}})
    assert status == 400 and "error" in payload
