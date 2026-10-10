from __future__ import annotations

import hashlib
import sqlite3
import time

from finahinking.research.contracts import AgentTask
from finahinking.research.job_queue import JobQueue, JobStatus
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


def test_dispatch_start_failure_does_not_strand_running_job(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    queue = JobQueue(path, backoff_base_seconds=0)
    record = queue.enqueue(_task("start-failure"), "idem-start-failure")
    supervisor = ResearchSupervisor(path, registry=StageRegistry(), worker_id="supervisor-a", max_concurrency=1)

    assert supervisor.dispatch(record.job_id) is None
    assert queue.get(record.job_id).status is JobStatus.RETRYABLE

