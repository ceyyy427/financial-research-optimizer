"""Bounded local worker for trusted, paper-only research runner functions.

Runners are application-owned Python callables, never model-provided code.
Each invocation executes in a disposable child process so timeouts terminate
late computation instead of permitting a detached thread to finish later.
Only a closed digest/reference result crosses back into the durable queue.
"""

from __future__ import annotations

import json
import math
import multiprocessing
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import AgentTask, stable_digest
from .job_queue import JobQueue, JobRecord, JobStatus, _ref


class WorkerStatus(str, Enum):
    IDLE = "idle"
    COMPLETED = "completed"
    RETRYABLE = "retryable"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class WorkerResult:
    status: WorkerStatus
    job_id: str | None = None
    result_ref: str | None = None
    failure_kind: str | None = None
    message_digest: str | None = None
    attempts: int = 0


_RESULT_FIELDS = frozenset({"status", "result_ref", "checkpoint_ref", "report_ref", "learning_ref", "ledger_ref"})


def _invoke_child(connection: Any, runner: Callable[..., Any], task: AgentTask, checkpoint_ref: str | None, max_result_bytes: int) -> None:
    """Send JSON only; exceptions and arbitrary objects never cross IPC."""
    try:
        value = runner(task, checkpoint_ref)
        if not isinstance(value, Mapping) or set(value) - _RESULT_FIELDS:
            connection.send_bytes(b'{"failure":"RESULT_INVALID"}')
            return
        if value.get("status") != "completed" or "result_ref" not in value:
            connection.send_bytes(b'{"failure":"RESULT_INVALID"}')
            return
        try:
            clean = {key: _ref(item, key) for key, item in value.items() if key != "status" and item is not None}
        except (TypeError, ValueError):
            connection.send_bytes(b'{"failure":"RESULT_INVALID"}')
            return
        encoded = json.dumps({"status": "completed", **clean}, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(encoded) > max_result_bytes:
            connection.send_bytes(b'{"failure":"RESOURCE_LIMIT"}')
            return
        connection.send_bytes(encoded)
    except Exception:  # noqa: BLE001 - never serialize exception text
        connection.send_bytes(b'{"failure":"RUNNER_FAILED"}')
    finally:
        connection.close()


class ResearchWorker:
    """Execute one leased job using bounded application-owned computation.

``task_resolver`` is required after restart because the queue persists only a
task reference/digest. Runners return references to immutable artifacts; they
must not publish side effects. Queue completion is the sole publication of
report/learning/ledger references and is idempotent.
"""

    def __init__(
        self,
        queue: JobQueue,
        *,
        runner: Callable[[AgentTask, str | None], Mapping[str, str]],
        worker_id: str,
        task_resolver: Callable[[str], AgentTask] | None = None,
        timeout_seconds: float = 60.0,
        max_result_bytes: int = 8192,
        max_jobs: int = 100,
    ) -> None:
        if not isinstance(queue, JobQueue) or not callable(runner):
            raise TypeError("queue and trusted runner are required")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in (max_result_bytes, max_jobs)):
            raise ValueError("worker resource limits must be positive integers")
        self.queue = queue
        self.runner = runner
        self.worker_id = _ref(worker_id, "worker_id")
        self.task_resolver = task_resolver or queue.resolve_task
        self.timeout_seconds = float(timeout_seconds)
        self.max_result_bytes = max_result_bytes
        self.max_jobs = max_jobs
        self._executed = 0

    def run_once(self) -> WorkerResult:
        if self._executed >= self.max_jobs:
            return WorkerResult(WorkerStatus.IDLE, failure_kind="RESOURCE_LIMIT", message_digest=stable_digest("RESOURCE_LIMIT"))
        job = self.queue.claim(self.worker_id)
        if job is None:
            return WorkerResult(WorkerStatus.IDLE)
        self._executed += 1
        try:
            task = self.task_resolver(job.task_ref)
            if not isinstance(task, AgentTask) or self.queue._task_digest(task) != job.task_digest:
                return self._fail(job, "TASK_IDENTITY_MISMATCH", retryable=False)
        except Exception:  # noqa: BLE001 - resolver failures remain digest-only
            return self._fail(job, "TASK_UNAVAILABLE", retryable=False)
        if self.queue.is_cancel_requested(job.job_id):
            cancelled = self.queue.mark_cancelled(job.job_id)
            return WorkerResult(WorkerStatus.CANCELLED, job.job_id, attempts=cancelled.attempts)

        # Lease must outlive this attempt. A stricter queue lease prevents two
        # workers from simultaneously publishing the same logical job.
        deadline = min(self.timeout_seconds, task.timeout_seconds, self.queue.lease_seconds)
        context = multiprocessing.get_context("fork")
        parent, child = context.Pipe(duplex=False)
        process = context.Process(target=_invoke_child, args=(child, self.runner, task, job.checkpoint_ref, self.max_result_bytes), daemon=True)
        process.start()
        child.close()
        started = time.monotonic()
        payload: Mapping[str, Any] | None = None
        failure: str | None = None
        try:
            while time.monotonic() - started < deadline:
                if self.queue.is_cancel_requested(job.job_id):
                    failure = "CANCELLED"
                    break
                if parent.poll(min(0.01, max(0.0, deadline - (time.monotonic() - started)))):
                    try:
                        encoded = parent.recv_bytes(maxlength=self.max_result_bytes)
                        payload = json.loads(encoded)
                    except (EOFError, OSError, UnicodeError, json.JSONDecodeError):
                        failure = "RESULT_INVALID"
                    break
                if not process.is_alive():
                    failure = "RUNNER_FAILED"
                    break
            else:
                failure = "TIMEOUT"
        finally:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            parent.close()
        if failure == "CANCELLED":
            cancelled = self.queue.mark_cancelled(job.job_id)
            return WorkerResult(WorkerStatus.CANCELLED, job.job_id, attempts=cancelled.attempts)
        if failure is not None:
            return self._fail(job, failure, retryable=failure in {"TIMEOUT", "RUNNER_FAILED"})
        if not isinstance(payload, Mapping):
            return self._fail(job, "RESULT_INVALID", retryable=False)
        if "failure" in payload:
            kind = str(payload["failure"])
            return self._fail(job, kind, retryable=kind == "RUNNER_FAILED")
        try:
            if set(payload) - _RESULT_FIELDS or payload.get("status") != "completed":
                raise ValueError("invalid result fields")
            refs = {key: _ref(value, key) for key, value in payload.items() if key != "status"}
            completed = self.queue.complete(job.job_id, **refs)
        except (TypeError, ValueError):
            return self._fail(job, "RESULT_INVALID", retryable=False)
        status = WorkerStatus.CANCELLED if completed.status is JobStatus.CANCELLED else WorkerStatus.COMPLETED
        return WorkerResult(status, completed.job_id, completed.result_ref, attempts=completed.attempts)

    def _fail(self, job: JobRecord, kind: str, *, retryable: bool) -> WorkerResult:
        if not retryable:
            # A rejected result is a permanent failure, not a repeated attempt.
            failed = self.queue.fail(job.job_id, kind)
        else:
            failed = self.queue.retry(job.job_id, kind)
        status = WorkerStatus.RETRYABLE if failed.status is JobStatus.RETRYABLE else WorkerStatus.FAILED
        return WorkerResult(status, job.job_id, failure_kind=kind, message_digest=stable_digest(kind), attempts=failed.attempts)


__all__ = ["ResearchWorker", "WorkerResult", "WorkerStatus"]
