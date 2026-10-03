from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from finahinking.local_app import LocalAppConfig, LocalApplication


def test_event_projection_contains_full_evidence_bound_journey_and_is_idempotent() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    event = app.route("GET", "/api/events")[2]["events"][0]
    for key in ("claims", "evidence", "show_evidence", "what_changed", "why_it_may_matter", "knowledge_bridge", "quant_evidence", "conclusion_ladder", "learning_card"):
        assert event.get(key), key
    first = app.route("POST", "/api/events/learn", body={})
    second = app.route("POST", "/api/events/learn", body={})
    assert first[0] == second[0] == 201
    assert first[2]["event_id"] == second[2]["event_id"]
    personal = app.personal()
    assert any(node["node_type"] == "event" for node in personal["nodes"])
    assert personal["history"]
    app.close()


def test_concept_page_renders_all_eight_levels_and_learning_action() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    page = app.route("GET", "/knowledge/volatility")[2]
    for label in ("Intuition", "Formal", "Equation", "Derivation", "Code", "Finance", "Quant", "Current context"):
        assert label in page
    assert "name=\"outcome\"" in page
    assert "/api/personal/save" in page
    app.close()


def test_quant_and_strategy_are_real_research_artifacts() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    quant = app.route("POST", "/api/quant", body={"question": "Does beta explain the sample?"})
    assert quant[0] == 200
    assert quant[2]["stage"] == "result"
    assert quant[2]["result"]["observations"] >= 40
    assert quant[2]["result"]["slope"] is not None
    strategy = app.route("POST", "/api/strategy", body={"idea": "moving average trend"})
    assert strategy[0] == 200
    assert strategy[2]["strategy_spec"]["reviewed"] is True
    assert strategy[2]["backtest"]["metrics"]
    assert strategy[2]["oos"]["metrics"]
    assert strategy[2]["paper"]["status"] == "PAPER_ONLY"
    assert strategy[2]["real_money"] is False
    app.close()


def test_rendered_worlds_expose_actions_and_explicit_projection_language() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    for path in ("/events", "/quant", "/strategy", "/personal", "/community"):
        page = app.route("GET", path)[2]
        assert "form" in page.lower(), path
    assert "explicit projection" in app.route("GET", "/community")[2].lower()
    app.close()


def test_knowledge_pages_are_total_and_loopback_binding_is_enforced() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    for concept_id in (item.concept_id for item in __import__("finahinking.p7_5.knowledge", fromlist=["DEFAULT_CATALOG"]).DEFAULT_CATALOG.concepts):
        assert app.route("GET", f"/knowledge/{concept_id}")[0] == 200
    app.close()
    with pytest.raises(ValueError, match="loopback"):
        LocalAppConfig(host="0.0.0.0")


def test_event_projection_requires_consent_and_is_allow_listed() -> None:
    app = LocalApplication(connection=sqlite3.connect(":memory:"))
    app.route("POST", "/api/events/learn", body={})
    denied = app.route("POST", "/api/community/project", body={})
    assert denied[0] == 403
    projected = app.route("POST", "/api/community/project", body={"consent": "true"})
    assert projected[0] == 201
    assert projected[2]["consented"] is True
    app.close()


def test_research_artifact_can_be_reopened_after_process_restart(tmp_path) -> None:
    db = tmp_path / "finahinking.sqlite3"
    first = LocalApplication(LocalAppConfig(db_path=str(db)))
    run = first.route("POST", "/api/quant", body={"question": "Does beta explain the sample?"})[2]
    node_id = run["node_id"]
    first.close()
    reopened = LocalApplication(LocalAppConfig(db_path=str(db)))
    status, _, artifact = reopened.route("GET", f"/api/research/artifacts/{node_id}")
    assert status == 200 and artifact["node_id"] == node_id and artifact["artifact_fingerprint"]
    assert Path(artifact["artifact_path"]).is_file()
    reopened.close()


def test_diagnostic_bundle_and_private_backup_are_redacted_and_replayable(tmp_path) -> None:
    app = LocalApplication(LocalAppConfig(db_path=str(tmp_path / "app.sqlite3")))
    app.route("POST", "/api/personal/save", body={"title": "private", "payload": {"secret_note": "do not share"}})
    bundle = app.route("GET", "/api/diagnostics/bundle")[2]
    assert bundle["privacy"]["database_path"] == "redacted"
    assert "secret_note" not in str(bundle)
    backup = app.route("GET", "/api/personal/backup")[2]
    assert backup["private"] is True and Path(backup["backup_path"]).is_file()
    app.close()
