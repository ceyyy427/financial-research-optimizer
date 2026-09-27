import json
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from financial_research.run_store import IdempotencyConflictError, StoreBusyError, RunStore
from financial_research.sqlite_run_store import SqliteRunStore
from agent.executor import execute_plan


def _create(store, **kwargs):
    return store.create_with_result("synthetic research", "forecasting", "standard", request={"x": 1}, **kwargs)


def test_json_idempotency_and_conflict_are_atomic(tmp_path):
    store = RunStore(tmp_path / "json")
    first = _create(store, client_id="client-a", tenant_id="tenant-a", idempotency_key="request-1")
    second = _create(store, client_id="client-a", tenant_id="tenant-a", idempotency_key="request-1")
    assert second["reused"] is True
    assert second["run_id"] == first["run_id"]
    other_tenant = _create(store, client_id="client-a", tenant_id="tenant-b", idempotency_key="request-1")
    assert other_tenant["run_id"] != first["run_id"]
    with pytest.raises(IdempotencyConflictError):
        store.create_with_result("different research", "forecasting", "standard", request={"x": 2}, client_id="client-a", tenant_id="tenant-a", idempotency_key="request-1")


def test_json_manifest_remains_valid_under_concurrent_writers(tmp_path):
    store = RunStore(tmp_path / "json")
    run_id = _create(store)["run_id"]
    run_dir = store.run_dir(run_id)
    for index in range(20):
        (run_dir / f"artifact_{index}.json").write_text(json.dumps({"index": index}), encoding="utf-8")

    def register(index):
        return store.register_artifacts(run_id, [f"artifact_{index}.json"])

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(register, range(20)))
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    names = {item["name"] for item in manifest["artifacts"]}
    assert {f"artifact_{index}.json" for index in range(20)} <= names
    assert (run_dir / "manifest.json").read_text(encoding="utf-8").strip().startswith("{")


def test_lease_busy_and_stale_recovery(tmp_path):
    store = RunStore(tmp_path / "json")
    run_id = _create(store)["run_id"]
    store.acquire_lease(run_id, "worker-a", ttl_seconds=1)
    with pytest.raises(StoreBusyError):
        store.acquire_lease(run_id, "worker-b", ttl_seconds=1)
    time.sleep(1.1)
    assert run_id in store.recover_stale_runs()
    store.acquire_lease(run_id, "worker-b", ttl_seconds=5)
    store.release_lease(run_id, "worker-b", status="completed")
    assert store.status(run_id)["status"] == "completed"


def test_checkpoint_is_persisted_and_rejects_run_or_plan_mismatch(tmp_path):
    store = RunStore(tmp_path / "json")
    run_id = _create(store)["run_id"]
    plan = {
        "plan_id": "plan-1",
        "immutable_contract": {"run_id": run_id, "target": "x"},
        "nodes": [{"id": "work", "tool": "work", "depends_on": [], "max_retries": 0, "timeout_seconds": 1, "budget": {}, "artifacts": []}],
    }
    execute_plan(plan, handlers={"work": lambda contract, node: {"status": "passed"}}, run_store=store, run_id=run_id)
    checkpoint = store.load_checkpoint(run_id)
    assert checkpoint["run_id"] == run_id
    assert checkpoint["schema_version"] == "checkpoint.v2"
    changed = {**plan, "immutable_contract": {"run_id": run_id, "target": "changed"}}
    with pytest.raises(ValueError, match="checkpoint_mismatch"):
        execute_plan(changed, handlers={"work": lambda contract, node: {"status": "passed"}}, run_store=store, run_id=run_id)


@pytest.mark.parametrize("store_cls", [RunStore, SqliteRunStore])
def test_backend_contract_has_common_lifecycle_surface(tmp_path, store_cls):
    store = store_cls(tmp_path / store_cls.__name__)
    created = _create(store, client_id="client", idempotency_key="same")
    run_id = created["run_id"]
    store.save_contract(run_id, {"run_id": run_id, "schema_version": "1"})
    store.save_plan(run_id, {"plan_id": "p", "nodes": []})
    store.acquire_lease(run_id, "worker", ttl_seconds=5)
    store.heartbeat_lease(run_id, "worker", ttl_seconds=5)
    store.release_lease(run_id, "worker", status="completed")
    result = store.status(run_id)
    assert result["run_id"] == run_id
    assert result["status"] == "completed"
    assert store.get(run_id)["request_hash"]
    if isinstance(store, SqliteRunStore):
        with store._connect() as db:
            assert db.execute("SELECT COUNT(*) FROM run_events WHERE run_id=?", (run_id,)).fetchone()[0] >= 1
