from __future__ import annotations

import pytest

from finahinking.research.contracts import AgentTask
from finahinking.research.job_queue import JobQueue, JobStatus


def task(task_id: str = "task-1") -> AgentTask:
    return AgentTask(
        role="technical",
        task_id=task_id,
        input_digest=f"input-{task_id}",
        inputs={"dataset_ref": "dataset-1"},
    )


def test_enqueue_is_idempotent_and_does_not_persist_task_inputs(tmp_path) -> None:
    queue = JobQueue(tmp_path / "jobs.sqlite")
    first = queue.enqueue(task(), "idem-1")
    again = queue.enqueue(task(), "idem-1")

    assert first == again
    assert first.status is JobStatus.QUEUED
    raw = (tmp_path / "jobs.sqlite").read_bytes()
    assert b"dataset_ref" not in raw
    assert b"prompt" not in raw


def test_claim_transitions_and_crash_recovery(tmp_path) -> None:
    now = [100.0]
    queue = JobQueue(tmp_path / "jobs.sqlite", clock=lambda: now[0], lease_seconds=5)
    queued = queue.enqueue(task(), "idem-1")
    running = queue.claim("worker-a")
    assert running is not None and running.status is JobStatus.RUNNING
    assert queue.claim("worker-b") is None

    now[0] = 106.0
    recovered = queue.claim("worker-b")
    assert recovered is not None
    assert recovered.job_id == queued.job_id
    assert recovered.attempts == 2


def test_retry_backoff_cancel_and_terminal_transitions(tmp_path) -> None:
    now = [100.0]
    queue = JobQueue(tmp_path / "jobs.sqlite", clock=lambda: now[0], backoff_base_seconds=10)
    record = queue.enqueue(task(), "idem-1")
    queue.claim("worker-a")
    retried = queue.retry(record.job_id, "temporary failure")
    assert retried.status is JobStatus.RETRYABLE
    assert retried.available_at == 110.0
    assert retried.last_error_digest
    assert queue.cancel(record.job_id).status is JobStatus.CANCELLED
    with pytest.raises(ValueError):
        queue.retry(record.job_id, "must not revive")


def test_queue_reopens_and_preserves_only_references(tmp_path) -> None:
    path = tmp_path / "jobs.sqlite"
    first = JobQueue(path)
    record = first.enqueue(task(), "idem-1")
    first.update_checkpoint(record.job_id, "checkpoint:abc123")
    reopened = JobQueue(path)
    loaded = reopened.get(record.job_id)
    assert loaded.checkpoint_ref == "checkpoint:abc123"
    assert loaded.task_ref == "task-1"

