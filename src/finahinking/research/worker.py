"""Bounded local worker for trusted, paper-only research runner functions.

Runners are application-owned Python callables, never model-provided code.
Each invocation executes in a disposable child process so timeouts terminate
late computation instead of permitting a detached thread to finish later.
Only a closed digest/reference result crosses back into the durable queue.
"""

from __future__ import annotations

import inspect
import json
import math
import multiprocessing
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import AgentTask, stable_digest
from .job_queue import JobQueue, JobRecord, JobStatus, StaleLeaseError, _ref
from .worker_entrypoint import SpawnWorkerHandle


def _spawn_callable(value: object) -> bool:
    return (
        inspect.isfunction(value)
        and value.__module__ not in {None, "__main__"}
        and value.__qualname__ == value.__name__
        and not value.__code__.co_freevars
    )


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
    checkpoint_ref: str | None = None


_RESULT_FIELDS = frozenset({"status", "result_ref", "checkpoint_ref", "report_ref", "learning_ref", "ledger_ref"})
_FAILURE_FIELDS = frozenset({"failure", "checkpoint_ref"})


def _invoke_child(
    connection: Any,
    resolver: Callable[[str], AgentTask] | None,
    runner: Callable[..., Any],
    task_ref: str,
    expected_digest: str,
    checkpoint_ref: str | None,
    max_result_bytes: int,
    task_snapshot: AgentTask | None = None,
) -> None:
    """Send JSON only; exceptions and arbitrary objects never cross IPC."""
    try:
        task = task_snapshot if task_snapshot is not None else resolver(task_ref)  # type: ignore[misc]
    except Exception:  # noqa: BLE001 - resolver details never cross the boundary
        connection.send_bytes(b'{"failure":"TASK_UNAVAILABLE"}')
        connection.close()
        return
    try:
        if not isinstance(task, AgentTask) or stable_digest(
            {
                "role": task.role,
                "task_id": task.task_id,
                "input_digest": task.input_digest,
                "capabilities": task.capabilities,
                "required": task.required,
                "timeout_seconds": task.timeout_seconds,
                "payload_digest": stable_digest(task.inputs),
            }
        ) != expected_digest:
            connection.send_bytes(b'{"failure":"TASK_IDENTITY_MISMATCH"}')
            return
        ready = json.dumps({"ready": True, "timeout_seconds": task.timeout_seconds}, separators=(",", ":"), allow_nan=False).encode("utf-8")
        connection.send_bytes(ready)
        def publish_checkpoint(reference: str) -> None:
            """Send a public checkpoint reference while the stage is running."""
            connection.send_bytes(
                json.dumps(
                    {"checkpoint_ref": _ref(reference, "checkpoint_ref")},
                    separators=(",", ":"),
                    allow_nan=False,
                ).encode("utf-8")
            )

        try:
            signature = inspect.signature(runner)
            accepts_callback = len(
                [parameter for parameter in signature.parameters.values() if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)]
            ) >= 3 or any(parameter.kind is parameter.VAR_POSITIONAL for parameter in signature.parameters.values())
        except (TypeError, ValueError):
            accepts_callback = False
        value = runner(task, checkpoint_ref, publish_checkpoint) if accepts_callback else runner(task, checkpoint_ref)
        if not isinstance(value, Mapping) or set(value) - _RESULT_FIELDS:
            if isinstance(value, Mapping) and set(value).issubset(_FAILURE_FIELDS) and isinstance(value.get("failure"), str):
                connection.send_bytes(json.dumps(dict(value), separators=(",", ":"), allow_nan=False).encode("utf-8"))
                return
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
        if not _spawn_callable(runner):
            raise ValueError("runner must be a module-level function for spawn")
        if task_resolver is not None and not _spawn_callable(task_resolver):
            raise ValueError("task_resolver must be a module-level function for spawn")
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

    def run_once(self, target_job_id: str | None = None) -> WorkerResult:
        if self._executed >= self.max_jobs:
            return WorkerResult(WorkerStatus.IDLE, failure_kind="RESOURCE_LIMIT", message_digest=stable_digest("RESOURCE_LIMIT"))
        job = self.queue.claim(self.worker_id, job_id=target_job_id)
        if job is None:
            return WorkerResult(WorkerStatus.IDLE)
        self._executed += 1
        if self.queue.is_cancel_requested(job.job_id):
            try:
                cancelled = self.queue.mark_cancelled(job.job_id, worker_id=job.worker_id, attempt=job.attempts, lease_until=job.lease_until, lease_token=job.lease_token)
            except StaleLeaseError:
                return self._stale(job)
            return WorkerResult(WorkerStatus.CANCELLED, job.job_id, attempts=cancelled.attempts)

        # Lease must outlive this attempt. A stricter queue lease prevents two
        # workers from simultaneously publishing the same logical job.
        deadline = min(self.timeout_seconds, self.queue.lease_seconds)
        # Legacy compatibility uses the same spawn-only boundary as the
        # Supervisor.  Production requests never instantiate this class.
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe(duplex=False)
        task_snapshot: AgentTask | None = None
        resolver: Callable[[str], AgentTask] | None = self.task_resolver
        # The queue's in-memory resolver is not a process contract. Resolve
        # its already-durable task in the owner and pass only the immutable
        # AgentTask snapshot; custom restart resolvers remain spawn-callable.
        if getattr(resolver, "__self__", None) is self.queue:
            task_snapshot = resolver(job.task_ref)
            resolver = None
        process = context.Process(target=_invoke_child, args=(child, resolver, self.runner, job.task_ref, job.task_digest, job.checkpoint_ref, self.max_result_bytes, task_snapshot), daemon=True)
        started = time.monotonic()
        overall_deadline = started + deadline
        task_deadline = overall_deadline
        process.start()
        child.close()
        payload: Mapping[str, Any] | None = None
        failure: str | None = None
        latest_checkpoint: str | None = job.checkpoint_ref
        try:
            while time.monotonic() < task_deadline:
                if self.queue.is_cancel_requested(job.job_id):
                    failure = "CANCELLED"
                    break
                remaining = max(0.0, task_deadline - time.monotonic())
                if parent.poll(min(0.01, remaining)):
                    try:
                        encoded = parent.recv_bytes(maxlength=self.max_result_bytes)
                        message = json.loads(encoded)
                        if isinstance(message, Mapping) and message.get("ready") is True:
                            task_timeout = float(message["timeout_seconds"])
                            if not math.isfinite(task_timeout) or task_timeout <= 0:
                                failure = "RESULT_INVALID"
                                break
                            task_deadline = min(overall_deadline, time.monotonic() + task_timeout)
                            continue
                        if isinstance(message, Mapping) and set(message) == {"checkpoint_ref"}:
                            checkpoint_ref = message.get("checkpoint_ref")
                            try:
                                checkpoint_ref = _ref(checkpoint_ref, "checkpoint_ref")
                                updated = self.queue.update_checkpoint(
                                    job.job_id,
                                    checkpoint_ref,
                                    worker_id=job.worker_id,
                                    attempt=job.attempts,
                                    lease_until=job.lease_until,
                                    lease_token=job.lease_token,
                                )
                            except (TypeError, ValueError, StaleLeaseError):
                                failure = "STALE_LEASE"
                                break
                            latest_checkpoint = updated.checkpoint_ref
                            continue
                        payload = message
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
            try:
                cancelled = self.queue.mark_cancelled(job.job_id, worker_id=job.worker_id, attempt=job.attempts, lease_until=job.lease_until, lease_token=job.lease_token)
            except StaleLeaseError:
                return self._stale(job)
            return WorkerResult(WorkerStatus.CANCELLED, job.job_id, attempts=cancelled.attempts)
        if failure is not None:
            if failure == "STALE_LEASE":
                return self._stale(job)
            return self._fail(job, failure, retryable=failure in {"TIMEOUT", "RUNNER_FAILED"})
        if not isinstance(payload, Mapping):
            return self._fail(job, "RESULT_INVALID", retryable=False)
        if "failure" in payload:
            kind = str(payload["failure"])
            if kind == "CANCELLED":
                try:
                    cancelled = self.queue.mark_cancelled(job.job_id, worker_id=job.worker_id, attempt=job.attempts, lease_until=job.lease_until, lease_token=job.lease_token)
                except StaleLeaseError:
                    return self._stale(job)
                return WorkerResult(WorkerStatus.CANCELLED, job.job_id, attempts=cancelled.attempts)
            return self._fail(job, kind, retryable=kind == "RUNNER_FAILED")
        try:
            if set(payload) - _RESULT_FIELDS or payload.get("status") != "completed":
                raise ValueError("invalid result fields")
            refs = {key: _ref(value, key) for key, value in payload.items() if key != "status"}
            completed = self.queue.complete(job.job_id, **refs, worker_id=job.worker_id, attempt=job.attempts, lease_until=job.lease_until, lease_token=job.lease_token)
        except (TypeError, ValueError):
            return self._fail(job, "RESULT_INVALID", retryable=False)
        except StaleLeaseError:
            return self._stale(job)
        status = WorkerStatus.CANCELLED if completed.status is JobStatus.CANCELLED else WorkerStatus.COMPLETED
        return WorkerResult(status, completed.job_id, completed.result_ref, attempts=completed.attempts, checkpoint_ref=completed.checkpoint_ref or latest_checkpoint)

    def _fail(self, job: JobRecord, kind: str, *, retryable: bool) -> WorkerResult:
        if not retryable:
            # A rejected result is a permanent failure, not a repeated attempt.
            try:
                failed = self.queue.fail(job.job_id, kind, worker_id=job.worker_id, attempt=job.attempts, lease_until=job.lease_until, lease_token=job.lease_token)
            except StaleLeaseError:
                return self._stale(job)
        else:
            try:
                failed = self.queue.retry(job.job_id, kind, worker_id=job.worker_id, attempt=job.attempts, lease_until=job.lease_until, lease_token=job.lease_token)
            except StaleLeaseError:
                return self._stale(job)
        status = WorkerStatus.RETRYABLE if failed.status is JobStatus.RETRYABLE else WorkerStatus.FAILED
        return WorkerResult(status, job.job_id, failure_kind=kind, message_digest=stable_digest(kind), attempts=failed.attempts)

    @staticmethod
    def _stale(job: JobRecord) -> WorkerResult:
        kind = "STALE_LEASE"
        return WorkerResult(WorkerStatus.FAILED, job.job_id, failure_kind=kind, message_digest=stable_digest(kind), attempts=job.attempts)


__all__ = ["ResearchWorker", "SpawnWorkerHandle", "WorkerResult", "WorkerStatus"]
