"""Independent owner of spawned research workers.

The supervisor is the only component that creates :class:`SpawnWorkerHandle`
instances.  Queue state is durable and every worker mutation is fenced by the
claimed attempt and lease token, so a restarted supervisor can safely recover
+orphaned jobs.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from .job_queue import JobQueue, JobRecord, JobStatus, StaleLeaseError
from .runtime_protocol import WorkerInvocation, WorkerMessage
from .stage_registry import StageRegistry, StageRegistryError
from .worker_entrypoint import SpawnWorkerHandle


class ResearchSupervisor:
    """Bounded scheduler for durable jobs and spawn workers."""

    def __init__(
        self,
        queue: JobQueue | str | Path,
        *,
        registry: StageRegistry,
        worker_id: str,
        max_concurrency: int,
        poll_interval: float = 0.05,
    ) -> None:
        if isinstance(queue, JobQueue):
            path = queue.path
        else:
            path = Path(queue)
        if not isinstance(registry, StageRegistry):
            raise TypeError("registry must be StageRegistry")
        if not isinstance(max_concurrency, int) or isinstance(max_concurrency, bool) or max_concurrency < 1:
            raise ValueError("max_concurrency must be positive")
        if not isinstance(poll_interval, (int, float)) or isinstance(poll_interval, bool) or poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self.queue = JobQueue(path)
        self.registry = registry
        self.worker_id = worker_id
        self.max_concurrency = max_concurrency
        self.poll_interval = float(poll_interval)
        self._handles: dict[str, tuple[SpawnWorkerHandle, JobRecord]] = {}
        self._messages: dict[str, WorkerMessage] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()

    @property
    def active_count(self) -> int:
        return len(self._handles)

    def start(self) -> None:
        """Start the supervisor loop in its own thread."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self.recover_orphans()
            self._thread = threading.Thread(target=self._loop, name="research-supervisor", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        if timeout < 0:
            raise ValueError("timeout must be non-negative")
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        for handle, _job in tuple(self._handles.values()):
            handle.cancel()
            handle.join()
        self._handles.clear()
        self._thread = None

    def recover_orphans(self) -> int:
        """Return expired leases to the durable queue and report their count."""
        return len(self.queue.recover_expired())

    def run_once(self) -> int:
        """Poll active workers and fill available concurrency slots."""
        self.recover_orphans()
        completed = 0
        for job_id, (handle, job) in tuple(self._handles.items()):
            # Renew before polling when the child is still active.  A short
            # lease is deliberately tolerated: stale workers fail closed.
            try:
                current = self.queue.get(job_id)
                if current.status is JobStatus.RUNNING and current.lease_until is not None and current.lease_until - time.time() < self.queue.lease_seconds / 2:
                        renewed = self.queue.heartbeat(
                            job_id,
                            worker_id=job.worker_id or self.worker_id,
                            attempt=job.attempts,
                            lease_until=current.lease_until,
                            lease_token=current.lease_token or "lease",
                        )
                        job = renewed
                        self._handles[job_id] = (handle, job)
            except (KeyError, StaleLeaseError):
                handle.cancel()
                handle.join()
                self._handles.pop(job_id, None)
                continue
            message = handle.poll(0)
            if message is None:
                continue
            self._messages[job_id] = message
            if message.kind in {"READY", "CHECKPOINT", "PROGRESS", "HEARTBEAT"}:
                if message.kind == "CHECKPOINT":
                    reference = message.payload.get("checkpoint_ref")
                    if isinstance(reference, str):
                        try:
                            updated = self.queue.update_checkpoint(
                                job_id, reference, worker_id=job.worker_id,
                                attempt=job.attempts, lease_until=job.lease_until,
                                lease_token=job.lease_token,
                            )
                            self._handles[job_id] = (handle, updated)
                        except (StaleLeaseError, ValueError):
                            handle.cancel()
                continue
            self._publish_terminal(job, message)
            handle.join()
            self._handles.pop(job_id, None)
            completed += 1

        while len(self._handles) < self.max_concurrency:
            job = self.queue.claim(self.worker_id)
            if job is None:
                break
            try:
                handle = self._make_handle(job)
                handle.start()
            except (OSError, RuntimeError, ValueError):
                self._retry_or_fail(job, "WORKER_START_FAILED")
                completed += 1
                continue
            self._handles[job.job_id] = (handle, job)
        return completed

    def dispatch(self, job_id: str | None = None) -> WorkerMessage | None:
        """Claim and synchronously drain one job, useful for deterministic callers."""
        job = self.queue.claim(self.worker_id, job_id=job_id)
        if job is None:
            return None
        handle: SpawnWorkerHandle | None = None
        try:
            handle = self._make_handle(job)
            handle.start()
            terminal: WorkerMessage | None = None
            while terminal is None:
                message = handle.poll(self.poll_interval)
                if message is None:
                    continue
                if message.kind == "CHECKPOINT":
                    reference = message.payload.get("checkpoint_ref")
                    if isinstance(reference, str):
                        self.queue.update_checkpoint(job.job_id, reference, worker_id=job.worker_id, attempt=job.attempts, lease_until=job.lease_until, lease_token=job.lease_token)
                elif message.kind in {"RESULT", "FAILED", "CANCELLED"}:
                    terminal = message
            self._publish_terminal(job, terminal)
            return terminal
        except (OSError, RuntimeError, ValueError, StageRegistryError):
            # A synchronous caller must not strand a claimed job in RUNNING
            # when registry admission or process startup fails.  Return the
            # job to the durable retry state under the same lease fence.
            self._retry_or_fail(job, "WORKER_START_FAILED")
            return None
        finally:
            if handle is not None:
                handle.join()

    def _make_handle(self, job: JobRecord) -> SpawnWorkerHandle:
        stage_names: tuple[str, ...] = ()
        try:
            task = self.queue.resolve_task(job.task_ref)
            requested = tuple(task.capabilities)
            if requested and all(self._registry_has(name) for name in requested):
                stage_names = requested
        except (KeyError, AttributeError):
            pass
        if not stage_names:
            names = tuple(spec.name for spec in self.registry.snapshot())
            if not names:
                raise ValueError("no registered research stage")
            stage_names = ("workflow",) if self._registry_has("workflow") else (names[0],)
        invocation = WorkerInvocation(
            job_id=job.job_id,
            task_ref=job.task_ref,
            task_digest=job.task_digest,
            checkpoint_ref=job.checkpoint_ref,
            stage_names=stage_names,
            timeout_seconds=max(0.01, float(job.lease_until - time.time()) if job.lease_until else 30.0),
            max_result_bytes=8192,
            budget={},
        )
        return SpawnWorkerHandle(invocation, registry=self.registry)

    def _registry_has(self, name: str) -> bool:
        try:
            self.registry.resolve(name)
        except StageRegistryError:
            return False
        return True

    def _publish_terminal(self, job: JobRecord, message: WorkerMessage) -> None:
        payload = message.payload
        fence = {"worker_id": job.worker_id, "attempt": job.attempts, "lease_until": job.lease_until, "lease_token": job.lease_token}
        try:
            if message.kind == "RESULT":
                result_ref = payload.get("result_ref")
                if isinstance(result_ref, str):
                    self.queue.complete(job.job_id, result_ref=result_ref, checkpoint_ref=job.checkpoint_ref, **fence)
                else:
                    self._retry_or_fail(job, "RESULT_INVALID")
            elif message.kind == "CANCELLED":
                self.queue.mark_cancelled(job.job_id, **fence)
            else:
                failure = str(payload.get("error_code", payload.get("failure_kind", "RUNNER_FAILED")))
                self._retry_or_fail(job, failure)
        except (StaleLeaseError, ValueError, KeyError):
            # Another supervisor already owns or published the job.  Terminal
            # publication is intentionally idempotent and fail closed.
            return

    def _retry_or_fail(self, job: JobRecord, reason: str) -> None:
        try:
            self.queue.retry(job.job_id, reason, worker_id=job.worker_id, attempt=job.attempts, lease_until=job.lease_until, lease_token=job.lease_token)
        except (StaleLeaseError, ValueError, KeyError):
            return

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.run_once()
            self._stop.wait(self.poll_interval)


__all__ = ["ResearchSupervisor"]
