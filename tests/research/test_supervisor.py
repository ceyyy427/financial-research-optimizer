from __future__ import annotations

import hashlib
import sqlite3
import time

import pytest

from finahinking.research.contracts import AgentTask
from finahinking.research.job_queue import JobQueue, JobStatus, StaleLeaseError
from finahinking.research.observability import current_runtime_budget
from finahinking.research.runtime_protocol import WorkerInvocation
from finahinking.research.stage_registry import StageRegistry, StageSpec
from finahinking.research.supervisor import ResearchSupervisor


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def stage_ok(invocation: WorkerInvocation) -> dict[str, object]:
    return {"status": "completed", "result_ref": f"artifact:{invocation.job_id}", "artifact_digest": _digest(invocation.job_id)}


def stage_slow(invocation: WorkerInvocation) -> dict[str, object]:
    time.sleep(0.08)
    return {"status": "completed", "result_ref": f"artifact:{invocation.job_id}", "artifact_digest": _digest(invocation.job_id)}


def stage_crash(invocation: WorkerInvocation) -> dict[str, object]:
    raise RuntimeError("opaque")


def stage_measured(invocation: WorkerInvocation) -> dict[str, object]:
    budget = current_runtime_budget()
    assert budget is not None
    count = 1 if invocation.task_ref.endswith("one") else 2
    budget.charge_experiments(count)
    for _ in range(count):
        budget.charge_provider_call(3)
    budget.charge_bytes(count * 7)
    time.sleep(0.04)
    return stage_ok(invocation)


def stage_checkpoint_then_wait(invocation: WorkerInvocation, checkpoint_ref, publish_checkpoint) -> dict[str, object]:
    del checkpoint_ref
    publish_checkpoint(f"checkpoint:{invocation.job_id}")
    time.sleep(10)
    return stage_ok(invocation)


def _drain(supervisor: ResearchSupervisor, queue: JobQueue, records, seconds=5.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        supervisor.run_once()
        if all(queue.get(item.job_id).status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED} for item in records):
            return
        time.sleep(0.005)
    raise AssertionError("spawn supervisor did not settle jobs")


def _task(name: str) -> AgentTask:
    return AgentTask(role="technical", task_id=name, input_digest=f"input-{name}")


def _registry(name: str, runner) -> StageRegistry:
    registry = StageRegistry()
    registry.register(StageSpec(name=name, version="1", runner_key=f"tests.{name}"), runner)
    return registry


def test_supervisor_completes_and_is_idempotent(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    queue = JobQueue(path)
    record = queue.enqueue(_task("one"), "idem-one")
    supervisor = ResearchSupervisor(path, registry=_registry("ok", stage_ok), worker_id="supervisor-a", max_concurrency=1)

    message = supervisor.dispatch(record.job_id)
    assert message is not None and message.kind == "RESULT"
    assert queue.get(record.job_id).status is JobStatus.COMPLETED
    # A second publication cannot replace the durable result.
    assert supervisor.dispatch(record.job_id) is None
    assert queue.get(record.job_id).result_ref == f"artifact:{record.job_id}"


def test_supervisor_bounds_concurrency_and_claims_atomically(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    queue = JobQueue(path)
    records = [queue.enqueue(_task(name), f"idem-{name}") for name in ("one", "two")]
    supervisor = ResearchSupervisor(path, registry=_registry("slow", stage_slow), worker_id="supervisor-a", max_concurrency=1, poll_interval=0.01)
    assert supervisor.run_once() == 0
    assert supervisor.active_count == 1
    # A second supervisor cannot claim the already running job.
    competing = ResearchSupervisor(path, registry=_registry("slow", stage_slow), worker_id="supervisor-b", max_concurrency=1)
    assert competing.run_once() == 0
    assert competing.active_count == 1 or competing.active_count == 0
    while supervisor.active_count:
        supervisor.run_once()
        time.sleep(0.01)
    assert queue.get(records[0].job_id).status is JobStatus.COMPLETED
    while competing.active_count:
        competing.run_once()
        time.sleep(0.01)
    assert all(queue.get(record.job_id).status is JobStatus.COMPLETED for record in records)


def test_supervisor_recovers_expired_orphan(tmp_path) -> None:
    now = [100.0]
    path = tmp_path / "jobs.sqlite"
    queue = JobQueue(path, clock=lambda: now[0], lease_seconds=1, backoff_base_seconds=0)
    record = queue.enqueue(_task("orphan"), "idem-orphan")
    claimed = queue.claim("dead-supervisor")
    assert claimed is not None
    now[0] = 102.0
    supervisor = ResearchSupervisor(path, registry=_registry("ok", stage_ok), worker_id="supervisor-a", max_concurrency=1)
    assert supervisor.recover_orphans() >= 1
    assert queue.get(record.job_id).status is JobStatus.RETRYABLE


def test_queue_heartbeat_uses_fence_and_wal(tmp_path) -> None:
    now = [100.0]
    path = tmp_path / "jobs.sqlite"
    queue = JobQueue(path, clock=lambda: now[0], lease_seconds=5)
    record = queue.enqueue(_task("heartbeat"), "idem-heartbeat")
    claimed = queue.claim("worker-a")
    assert claimed is not None
    now[0] = 101.0
    renewed = queue.heartbeat(record.job_id, worker_id="worker-a", attempt=claimed.attempts, lease_until=claimed.lease_until, lease_token=claimed.lease_token)
    assert renewed.lease_until == 106.0
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_expired_lease_is_recovered_and_stale_heartbeat_is_rejected(tmp_path) -> None:
    now = [50.0]
    queue = JobQueue(tmp_path / "jobs.sqlite", clock=lambda: now[0], lease_seconds=2, backoff_base_seconds=0)
    record = queue.enqueue(_task("expired"), "idem-expired")
    claimed = queue.claim("worker-a")
    assert claimed is not None
    now[0] = 53.0
    recovered = queue.recover_expired()
    assert recovered[0].job_id == record.job_id
    assert recovered[0].status is JobStatus.RETRYABLE
    with pytest.raises(StaleLeaseError):
        queue.heartbeat(record.job_id, worker_id="worker-a", attempt=claimed.attempts, lease_until=claimed.lease_until, lease_token=claimed.lease_token)


def test_concurrent_spawn_jobs_have_exact_independent_metrics(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite", max_attempts=1)
    records = [queue.enqueue(_task(name), f"idem-{name}") for name in ("measured-one", "measured-two")]
    supervisor = ResearchSupervisor(queue.path, registry=_registry("workflow", stage_measured), worker_id="metrics-owner", max_concurrency=2, budget={"max_experiments": 2, "max_provider_calls": 2, "max_bytes": 20})
    try:
        supervisor.run_once()
        assert supervisor.active_count == 2
        _drain(supervisor, queue, records)
        first, second = (supervisor.metrics_for(record.job_id) for record in records)
        assert first is not None and second is not None
        assert (first.experiments, first.provider_calls, first.bytes_used) == (1, 1, 10)
        assert (second.experiments, second.provider_calls, second.bytes_used) == (2, 2, 20)
        assert set(first.stage_durations) == set(second.stage_durations) == {"workflow"}
        assert first.stage_durations["workflow"] > 0
        assert all(queue.get(record.job_id).status is JobStatus.COMPLETED for record in records)
    finally:
        supervisor.stop()


@pytest.mark.parametrize("quota", [{"max_experiments": 1}, {"max_provider_calls": 1}, {"max_bytes": 10}])
def test_spawn_worker_limits_fail_closed(tmp_path, quota) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite", max_attempts=1)
    record = queue.enqueue(_task("measured-two"), "idem-limit")
    supervisor = ResearchSupervisor(queue.path, registry=_registry("workflow", stage_measured), worker_id="limits-owner", max_concurrency=1, budget=quota)
    message = supervisor.dispatch(record.job_id)
    assert message is not None and message.kind == "FAILED"
    assert message.payload["failure_kind"] == "RESOURCE_LIMIT"
    loaded = queue.get(record.job_id)
    assert loaded.status is JobStatus.FAILED
    assert loaded.result_ref is None


def test_cancellation_terminates_stage_and_retains_durable_checkpoint(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite", max_attempts=1)
    record = queue.enqueue(_task("checkpoint-cancel"), "idem-checkpoint-cancel")
    supervisor = ResearchSupervisor(queue.path, registry=_registry("workflow", stage_checkpoint_then_wait), worker_id="cancel-owner", max_concurrency=1)
    try:
        deadline = time.monotonic() + 3
        while queue.get(record.job_id).checkpoint_ref is None and time.monotonic() < deadline:
            supervisor.run_once()
            time.sleep(0.01)
        assert queue.get(record.job_id).checkpoint_ref == f"checkpoint:{record.job_id}"
        queue.cancel(record.job_id)
        _drain(supervisor, queue, [record])
        loaded = JobQueue(queue.path).get(record.job_id)
        assert loaded.status is JobStatus.CANCELLED
        assert loaded.result_ref is None
        assert loaded.checkpoint_ref == f"checkpoint:{record.job_id}"
        assert supervisor.active_count == 0
    finally:
        supervisor.stop()


def test_task_timeout_terminates_spawn_worker_without_result(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite", max_attempts=1)
    task = AgentTask(role="technical", task_id="timeout-task", input_digest="timeout-input", timeout_seconds=0.5)
    record = queue.enqueue(task, "idem-timeout")
    supervisor = ResearchSupervisor(queue, registry=_registry("workflow", stage_checkpoint_then_wait), worker_id="timeout-owner", max_concurrency=1)
    message = supervisor.dispatch(record.job_id)
    assert message is not None and message.kind == "FAILED"
    assert message.payload["error_code"] == "TIMEOUT"
    loaded = queue.get(record.job_id)
    assert loaded.status is JobStatus.FAILED
    assert loaded.result_ref is None


def test_heartbeat_keeps_long_stage_alive_past_initial_lease(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite", lease_seconds=0.1, max_attempts=1)
    record = queue.enqueue(_task("renewed"), "idem-renewed")
    supervisor = ResearchSupervisor(queue, registry=_registry("workflow", stage_slow), worker_id="heartbeat-owner", max_concurrency=1)
    try:
        _drain(supervisor, queue, [record])
        loaded = queue.get(record.job_id)
        assert loaded.status is JobStatus.COMPLETED
        with sqlite3.connect(queue.path) as db:
            assert db.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND status='heartbeat'", (record.job_id,)).fetchone()[0] > 0
    finally:
        supervisor.stop()


def test_dispatch_start_failure_does_not_strand_running_job(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    queue = JobQueue(path, backoff_base_seconds=0)
    record = queue.enqueue(_task("start-failure"), "idem-start-failure")
    supervisor = ResearchSupervisor(path, registry=StageRegistry(), worker_id="supervisor-a", max_concurrency=1)

    assert supervisor.dispatch(record.job_id) is None
    assert queue.get(record.job_id).status is JobStatus.RETRYABLE

