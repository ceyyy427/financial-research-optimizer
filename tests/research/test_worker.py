from __future__ import annotations

import time

import pytest

from finahinking.research.contracts import AgentTask
from finahinking.research.job_queue import JobQueue, JobStatus
from finahinking.research.worker import ResearchWorker, WorkerResult, WorkerStatus


def task(task_id: str = "task-1") -> AgentTask:
    return AgentTask(role="technical", task_id=task_id, input_digest=f"input-{task_id}")


def runner_complete(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
    if received.task_id != "task-1" or checkpoint_ref is not None:
        return {"failure": "RESULT_INVALID"}
    return {"status": "completed", "result_ref": "artifact:result-1", "checkpoint_ref": "checkpoint:next"}


def runner_slow(received: AgentTask, checkpoint_ref: str | None) -> None:
    del received, checkpoint_ref
    time.sleep(0.2)


def runner_resume(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
    del received
    return {"status": "completed", "result_ref": "artifact:resume-ok" if checkpoint_ref == "checkpoint:resume-1" else "artifact:resume-bad"}


def resolver_task(task_ref: str) -> AgentTask:
    return task(task_ref)


def resolver_sleep(task_ref: str) -> AgentTask:
    time.sleep(0.15)
    return task(task_ref)


def runner_late(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
    del received, checkpoint_ref
    time.sleep(0.15)
    return {"status": "completed", "result_ref": "artifact:late"}


def resolver_fail(task_ref: str) -> AgentTask:
    del task_ref
    raise RuntimeError("resolver failure")


def runner_never(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
    del received, checkpoint_ref
    return {"status": "completed", "result_ref": "artifact:never"}


def runner_unsafe(received: AgentTask, checkpoint_ref: str | None) -> dict[str, str]:
    del received, checkpoint_ref
    return {"status": "completed", "result_ref": "https://bad.example"}


def test_worker_completes_once_and_resumes_checkpoint(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    record = queue.enqueue(task(), "idem-1")
    result = ResearchWorker(queue, runner=runner_complete, worker_id="worker-a").run_once()
    assert isinstance(result, WorkerResult)
    assert result.status is WorkerStatus.COMPLETED
    assert queue.get(record.job_id).status is JobStatus.COMPLETED
    assert ResearchWorker(queue, runner=runner_complete, worker_id="worker-a").run_once().status is WorkerStatus.IDLE


def test_worker_timeout_retries_then_fails_without_leaking_result(tmp_path) -> None:
    now = [100.0]
    queue = JobQueue(tmp_path / "jobs.sqlite", clock=lambda: now[0], backoff_base_seconds=0, max_attempts=2)
    record = queue.enqueue(task(), "idem-1")

    worker = ResearchWorker(queue, runner=runner_slow, worker_id="worker-a", timeout_seconds=0.01)
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
    result = ResearchWorker(queue, runner=runner_never, worker_id="worker-a").run_once()
    assert result.status is WorkerStatus.IDLE
    assert queue.get(record.job_id).status is JobStatus.CANCELLED


def test_worker_passes_durable_checkpoint_reference_to_resolved_task(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    first_queue = JobQueue(path)
    record = first_queue.enqueue(task(), "idem-1")
    claimed = first_queue.claim("worker-a")
    assert claimed is not None
    first_queue.update_checkpoint(record.job_id, "checkpoint:resume-1", worker_id=claimed.worker_id, attempt=claimed.attempts, lease_until=claimed.lease_until, lease_token=claimed.lease_token)
    # Reopen returns the running lease to retryable after it expires; use a
    # fresh queue clock/short lease to model recovery before the worker runs.
    recovered = JobQueue(path, clock=lambda: claimed.lease_until + 1, lease_seconds=5)
    result = ResearchWorker(recovered, runner=runner_resume, task_resolver=resolver_task, worker_id="worker-a").run_once()
    assert result.status is WorkerStatus.COMPLETED
    assert result.result_ref == "artifact:resume-ok"


def test_resolver_is_inside_global_timeout(tmp_path) -> None:
    import time

    queue = JobQueue(tmp_path / "jobs.sqlite")
    queue.enqueue(task(), "idem-1")

    started = time.monotonic()
    result = ResearchWorker(queue, runner=runner_late, task_resolver=resolver_sleep, worker_id="worker-a", timeout_seconds=0.01).run_once()
    assert time.monotonic() - started < 1.0
    assert result.status is WorkerStatus.RETRYABLE


def test_task_timeout_is_enforced_inside_worker_global_budget(tmp_path) -> None:
    import time

    queue = JobQueue(tmp_path / "jobs.sqlite")
    short_task = AgentTask(role="technical", task_id="short", input_digest="short-input", timeout_seconds=0.01)
    queue.enqueue(short_task, "idem-short")

    started = time.monotonic()
    result = ResearchWorker(queue, runner=runner_late, worker_id="worker-a", timeout_seconds=0.5).run_once()
    assert time.monotonic() - started < 1.0
    assert result.status is WorkerStatus.RETRYABLE


def test_resolver_exception_is_permanent_task_unavailable(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    queue.enqueue(task(), "idem-1")

    result = ResearchWorker(queue, runner=runner_never, task_resolver=resolver_fail, worker_id="worker-a").run_once()
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

    result = ResearchWorker(queue, runner=runner_unsafe, worker_id="worker-a").run_once()
    assert result.status is WorkerStatus.FAILED
    assert queue.get(record.job_id).status is JobStatus.FAILED


def test_legacy_worker_rejects_nested_spawn_callables(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    with pytest.raises(ValueError, match="module-level"):
        ResearchWorker(queue, runner=lambda task, checkpoint: {"status": "completed", "result_ref": "artifact:x"}, worker_id="worker-a")
