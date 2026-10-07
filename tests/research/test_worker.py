from __future__ import annotations

import time

from finahinking.research.contracts import AgentTask
from finahinking.research.job_queue import JobQueue, JobStatus
from finahinking.research.worker import ResearchWorker, WorkerResult, WorkerStatus


def task(task_id: str = "task-1") -> AgentTask:
    return AgentTask(role="technical", task_id=task_id, input_digest=f"input-{task_id}")


def test_worker_completes_once_and_resumes_checkpoint(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    record = queue.enqueue(task(), "idem-1")
    def runner(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
        assert received.task_id == "task-1"
        assert checkpoint_ref is None
        return {"status": "completed", "result_ref": "artifact:result-1", "checkpoint_ref": "checkpoint:next"}

    result = ResearchWorker(queue, runner=runner, worker_id="worker-a").run_once()
    assert isinstance(result, WorkerResult)
    assert result.status is WorkerStatus.COMPLETED
    assert queue.get(record.job_id).status is JobStatus.COMPLETED
    assert ResearchWorker(queue, runner=runner, worker_id="worker-a").run_once().status is WorkerStatus.IDLE


def test_worker_timeout_retries_then_fails_without_leaking_result(tmp_path) -> None:
    now = [100.0]
    queue = JobQueue(tmp_path / "jobs.sqlite", clock=lambda: now[0], backoff_base_seconds=0, max_attempts=2)
    record = queue.enqueue(task(), "idem-1")

    def slow_runner(received: AgentTask, checkpoint_ref: str | None) -> None:
        time.sleep(0.2)

    worker = ResearchWorker(queue, runner=slow_runner, worker_id="worker-a", timeout_seconds=0.01)
    first = worker.run_once()
    assert first.status is WorkerStatus.RETRYABLE
    now[0] = 101.0
    second = worker.run_once()
    assert second.status is WorkerStatus.FAILED
    assert queue.get(record.job_id).status is JobStatus.FAILED


def test_worker_cancelled_job_does_not_publish_artifacts(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    record = queue.enqueue(task(), "idem-1")
    queue.cancel(record.job_id)
    published: list[str] = []

    def runner(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
        published.append("must-not-run")
        return {"status": "completed", "result_ref": "artifact:bad"}

    result = ResearchWorker(queue, runner=runner, worker_id="worker-a").run_once()
    assert result.status is WorkerStatus.IDLE
    assert published == []
    assert queue.get(record.job_id).status is JobStatus.CANCELLED


def test_worker_passes_durable_checkpoint_reference_to_resolved_task(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    first_queue = JobQueue(path)
    record = first_queue.enqueue(task(), "idem-1")
    claimed = first_queue.claim("worker-a")
    assert claimed is not None
    first_queue.update_checkpoint(record.job_id, "checkpoint:resume-1", worker_id=claimed.worker_id, attempt=claimed.attempts, lease_until=claimed.lease_until, lease_token=claimed.lease_token)
    def resolver(task_ref: str) -> AgentTask:
        return task(task_ref)

    def runner(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
        return {"status": "completed", "result_ref": "artifact:resume-ok" if checkpoint_ref == "checkpoint:resume-1" else "artifact:resume-bad"}

    # Reopen returns the running lease to retryable after it expires; use a
    # fresh queue clock/short lease to model recovery before the worker runs.
    recovered = JobQueue(path, clock=lambda: claimed.lease_until + 1, lease_seconds=5)
    result = ResearchWorker(recovered, runner=runner, task_resolver=resolver, worker_id="worker-a").run_once()
    assert result.status is WorkerStatus.COMPLETED
    assert result.result_ref == "artifact:resume-ok"


def test_resolver_is_inside_global_timeout(tmp_path) -> None:
    import time

    queue = JobQueue(tmp_path / "jobs.sqlite")
    queue.enqueue(task(), "idem-1")

    def resolver(task_ref: str) -> AgentTask:
        time.sleep(0.15)
        return task(task_ref)

    def runner(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
        return {"status": "completed", "result_ref": "artifact:late"}

    started = time.monotonic()
    result = ResearchWorker(queue, runner=runner, task_resolver=resolver, worker_id="worker-a", timeout_seconds=0.01).run_once()
    assert time.monotonic() - started < 0.1
    assert result.status is WorkerStatus.RETRYABLE


def test_task_timeout_is_enforced_inside_worker_global_budget(tmp_path) -> None:
    import time

    queue = JobQueue(tmp_path / "jobs.sqlite")
    short_task = AgentTask(role="technical", task_id="short", input_digest="short-input", timeout_seconds=0.01)
    queue.enqueue(short_task, "idem-short")

    def runner(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
        time.sleep(0.15)
        return {"status": "completed", "result_ref": "artifact:late"}

    started = time.monotonic()
    result = ResearchWorker(queue, runner=runner, worker_id="worker-a", timeout_seconds=0.5).run_once()
    assert time.monotonic() - started < 0.1
    assert result.status is WorkerStatus.RETRYABLE


def test_resolver_exception_is_permanent_task_unavailable(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    queue.enqueue(task(), "idem-1")

    def resolver(task_ref: str) -> AgentTask:
        raise RuntimeError("secret details must not cross boundary")

    def runner(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
        return {"status": "completed", "result_ref": "artifact:never"}

    result = ResearchWorker(queue, runner=runner, task_resolver=resolver, worker_id="worker-a").run_once()
    assert result.status is WorkerStatus.FAILED
    assert result.failure_kind == "TASK_UNAVAILABLE"
    assert queue.get(result.job_id).status is JobStatus.FAILED


def test_task_id_collision_is_rejected(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    queue.enqueue(task(), "idem-1")
    conflicting = AgentTask(role="technical", task_id="task-1", input_digest="different-input")
    import pytest
    with pytest.raises(ValueError, match="task_id"):
        queue.enqueue(conflicting, "idem-2")


def test_worker_rejects_unbounded_or_unsafe_result(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    record = queue.enqueue(task(), "idem-1")

    def unsafe_runner(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
        return {"status": "completed", "result_ref": "https://bad.example"}

    result = ResearchWorker(queue, runner=unsafe_runner, worker_id="worker-a").run_once()
    assert result.status is WorkerStatus.FAILED
    assert queue.get(record.job_id).status is JobStatus.FAILED
