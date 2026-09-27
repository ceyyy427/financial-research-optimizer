import asyncio
import json
import time
from pathlib import Path

import pytest

from agent.executor import execute_plan
from agent.handlers import HANDLERS, validate_handlers
from browser.auth_checkpoint import save_auth_checkpoint
from browser.cdp_session import CdpObserver
from build_refresh_plan import build_refresh_plan
from execute_online_refresh import execute_data_refresh
from online.http_cache import HttpCache


def _plan(tool="work", depends=None, **node_overrides):
    node = {
        "id": tool, "tool": tool, "depends_on": depends or [],
        "max_retries": 1, "timeout_seconds": 1,
        "budget": {"max_network_requests": 5, "max_artifacts": 5},
        "allow_degraded": False, "artifacts": [],
    }
    node.update(node_overrides)
    return {"plan_id": f"test-{tool}", "immutable_contract": {}, "nodes": [node]}


def test_missing_handlers_are_planning_only_and_default_registry_is_explicit():
    plan = _plan()
    result = execute_plan(plan, handlers={})
    assert result["status"] == "planning_only"
    assert all(item["execution_mode"] == "planning_only" for item in result["results"])
    assert validate_handlers(plan)["valid"] is False
    assert "discover_sources" in HANDLERS


def test_executor_retries_and_checkpoints(tmp_path):
    calls = {"n": 0}

    def handler(contract, node):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return {"status": "passed", "message": "ok", "artifacts": []}

    checkpoint = tmp_path / "checkpoint.json"
    result = execute_plan(_plan(), handlers={"work": handler}, checkpoint_path=checkpoint)
    assert result["status"] == "completed"
    assert calls["n"] == 2
    saved = json.loads(checkpoint.read_text())
    assert saved["statuses"]["work"] == "passed"
    assert saved["checkpoint_version"] == 2
    assert saved["plan_hash"]
    assert saved["contract_hash"]


def test_checkpoint_rejects_plan_or_contract_drift(tmp_path):
    checkpoint = tmp_path / "checkpoint.json"
    plan = _plan()
    execute_plan(plan, handlers={"work": lambda contract, node: {"status": "passed"}}, checkpoint_path=checkpoint)
    changed = dict(plan)
    changed["immutable_contract"] = {"target": "changed"}
    with pytest.raises(ValueError, match="cannot resume safely"):
        execute_plan(changed, handlers={"work": lambda contract, node: {"status": "passed"}}, checkpoint_path=checkpoint)


def test_global_budget_is_reserved_atomically_for_parallel_nodes():
    plan = {
        "plan_id": "budget-test",
        "immutable_contract": {"global_budget": {"max_network_requests": 1, "max_artifacts": 10}},
        "nodes": [
            {"id": "a", "tool": "work", "depends_on": [], "max_retries": 0, "timeout_seconds": 1, "budget": {"max_network_requests": 5, "max_artifacts": 5}, "artifacts": []},
            {"id": "b", "tool": "work", "depends_on": [], "max_retries": 0, "timeout_seconds": 1, "budget": {"max_network_requests": 5, "max_artifacts": 5}, "artifacts": []},
        ],
    }
    result = execute_plan(plan, handlers={"work": lambda contract, node: {"status": "passed", "network_requests": 1}}, max_workers=2)
    assert result["status"] == "blocked"
    assert sum(item.get("network_requests", 0) for item in result["results"]) == 1
    assert any(item.get("failure_class") == "global_budget" for item in result["results"])


def test_executor_timeout_is_failure_without_waiting_for_handler():
    def slow(contract, node):
        time.sleep(0.2)
        return {"status": "passed"}

    started = time.monotonic()
    result = execute_plan(_plan(timeout_seconds=0), handlers={"work": slow})
    elapsed = time.monotonic() - started
    assert result["status"] == "failed"
    assert result["results"][0]["failure_class"] == "timeout"
    assert elapsed < 0.35


def test_refresh_plan_separates_retrain():
    result = build_refresh_plan({"mode": "forecasting", "refresh_policy": {}}, now="2026-09-27T00:00:00+00:00")
    retrain = next(item for item in result["stages"] if item["stage"] == "model_retrain")
    assert retrain["automatic"] is False
    assert "without_retraining" in next(item for item in result["stages"] if item["stage"] == "feature_refresh")["action"]
    assert execute_data_refresh("fred", "https://example.test", "/tmp/fro-test", retrain=True)["status"] == "blocked"


def test_data_refresh_acquire_snapshot_parse_and_canonicalize(tmp_path):
    def transport(method, url, headers, timeout):
        return 200, {"content-type": "application/json"}, b'{"data":[{"indicator":"CPI","date":"2026-08-01","release_date":"2026-09-10T12:30:00Z","value":101.2,"unit":"%"}]}'

    result = execute_data_refresh("stats_gov_cn", "https://data.stats.gov.cn/api/cpi", tmp_path, transport=transport)
    assert result["status"] == "passed"
    assert result["normalized_rows"] == 1
    assert Path(result["normalized_file"]).exists()


def test_data_refresh_uses_source_specific_fred_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "test-key")

    def transport(method, url, headers, timeout):
        assert "api.stlouisfed.org/fred/series/observations" in url
        assert "series_id=GDP" in url
        return 200, {"content-type": "application/json"}, b'{"series_id":"GDP","observations":[{"date":"2026-09-25","value":"1.2","realtime_start":"2026-09-26"}]}'

    result = execute_data_refresh("fred", "https://ignored.example", tmp_path, params={"series_id": "GDP"}, transport=transport)
    assert result["status"] == "passed"
    assert result["source_id"] == "fred"
    assert result["normalized_rows"] == 1


class _AuthContext:
    async def storage_state(self):
        return {"cookies": [{"name": "session", "value": "DO_NOT_LEAK", "domain": "example.test"}], "origins": [{"origin": "https://example.test", "localStorage": [{"name": "x", "value": "secret"}]}]}


def test_auth_checkpoint_separates_private_state(tmp_path):
    async def run():
        return await save_auth_checkpoint(_AuthContext(), tmp_path / "auth_manifest.safe.json", allow_persist=True)
    result = asyncio.run(run())
    assert (tmp_path / "auth_state.private.json").exists()
    safe = (tmp_path / "auth_manifest.safe.json").read_text()
    assert "DO_NOT_LEAK" not in safe
    assert result["sensitive_values_persisted"] is True


class _Session:
    def __init__(self):
        self.listeners = {}
        self.commands = []

    async def send(self, command, params=None):
        self.commands.append(command)
        if command == "Network.getResponseBody":
            assert "Network.loadingFinished" in self.commands
            return {"body": '{"ok":true}'}
        return {}

    def on(self, event, callback):
        self.listeners[event] = callback


class _Context:
    def __init__(self, session):
        self.session = session

    async def new_cdp_session(self, page):
        return self.session


class _Page:
    url = "https://example.test"

    def __init__(self, session):
        self.context = _Context(session)


def test_cdp_captures_body_only_after_loading_finished(tmp_path):
    async def run():
        session = _Session()
        observer = CdpObserver(_Page(session), "example", capture_bodies=True, raw_body_dir=tmp_path / "bodies")
        await observer.start()
        session.listeners["Network.requestWillBeSent"]({"requestId": "r1", "request": {"method": "GET", "headers": {}}})
        session.listeners["Network.responseReceived"]({"requestId": "r1", "response": {"url": "https://example.test/data", "status": 200, "headers": {"content-type": "application/json"}}})
        assert "Network.getResponseBody" not in session.commands
        session.listeners["Network.loadingFinished"]({"requestId": "r1"})
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await observer.stop()
        return observer, session
    observer, session = asyncio.run(run())
    record = observer.recorder.records[0]
    assert "body" not in record
    assert Path(record["body_file"]).exists()
    assert "Network.getResponseBody" in session.commands
