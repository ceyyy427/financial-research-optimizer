from __future__ import annotations

import json
import sqlite3

from finahinking.local_app import LocalAppConfig, LocalApplication


def test_local_shell_defaults_to_offline_sample_mode() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    assert app.route("GET", "/health")[0] == 200
    diagnostics = app.route("GET", "/api/diagnostics")[2]
    assert diagnostics["database"] == "sqlite"
    assert diagnostics["offline"] is True
    assert diagnostics["real_money_execution"] is False
    assert app.route("GET", "/")[1].startswith("text/html")
    assert "Skip to content" in app.route("GET", "/")[2]
    app.close()


def test_normal_config_is_file_backed_for_restart_continuity() -> None:
    config = LocalAppConfig()
    assert config.db_path != ":memory:"
    assert config.db_path.endswith("finahinking.sqlite3")


def test_routes_expose_each_product_world_and_structured_knowledge() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    for path in ("/", "/events", "/knowledge", "/quant", "/strategy", "/personal", "/community", "/diagnostics"):
        status, content_type, payload = app.route("GET", path)
        assert status == 200
        assert content_type.startswith("text/html")
        assert "Finahinking" in payload
    payload = app.route("GET", "/api/knowledge", query={"q": ["volatility"]})[2]
    assert payload["concepts"][0]["id"] == "volatility"
    concept = app.route("GET", "/api/concepts/volatility")[2]
    assert concept["derivation"]
    assert concept["equation"]
    closure = app.route("GET", "/api/concepts/volatility/prerequisites")[2]
    assert closure["concepts"][-1]["concept_id"] == "volatility"
    path = app.route("GET", "/api/knowledge/path/reference-curriculum")[2]
    assert len(path["concept_ids"]) >= 15
    app.close()


def test_personal_save_and_reopen_use_the_same_p7_store(tmp_path) -> None:
    db = tmp_path / "finahinking.sqlite3"
    first = LocalApplication(LocalAppConfig(db_path=str(db)))
    status, _, result = first.route(
        "POST",
        "/api/personal/save",
        body={"title": "CPI review", "node_type": "note", "payload": {"mode": "SAMPLE"}},
    )
    assert status == 201
    assert result["saved"] is True
    first.close()

    reopened = LocalApplication(LocalAppConfig(db_path=str(db)))
    status, _, exported = reopened.route("GET", "/api/personal")
    assert status == 200
    assert any(item["title"] == "CPI review" for item in exported["nodes"])
    status, _, payload = reopened.route("POST", "/api/reopen", body={})
    assert status == 200 and payload["reopened"] is True
    reopened.close()


def test_api_rejects_invalid_payload_without_sql_or_network() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    status, content_type, payload = app.route("POST", "/api/personal/save", body={"title": ""})
    assert (status, content_type) == (400, "application/json")
    assert "required" in payload["error"]
    assert json.dumps(app.diagnostics())[0] == "{"
    app.close()
