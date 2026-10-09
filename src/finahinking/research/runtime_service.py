"""Durable composition boundary for long-running paper research jobs.

The service keeps queue records and stage journals reference-only.  Request
payloads are resolved from an application-owned callback after a restart, and
trusted stage callables return digests/references only.  A worker child is
bounded and can publish a checkpoint reference while a stage is running.
"""

from __future__ import annotations

import inspect
import math
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import AgentTask, ResearchRequest, stable_digest
from .drivers import OfflineDriver
from .job_queue import JobQueue, JobRecord, JobStatus, _ref
from .observability import RuntimeBudget, RuntimeLimitExceeded, RuntimeMetrics, bind_runtime_budget
from .provider_adapters import ProviderAdapterError, ProviderFailureKind
from .tools import ResearchToolGateway
from .worker import ResearchWorker, WorkerResult, WorkerStatus
from .workflow import ResearchOrchestrator


@dataclass(frozen=True, slots=True)
class RuntimeLimits:
    """Bound one service call and its provider/factor work."""

    max_wall_seconds: float = 300.0
    max_attempts: int = 100
    max_provider_calls: int | None = None
    max_bytes: int | None = None
    max_experiments: int | None = None
    max_concurrency: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.max_wall_seconds, bool) or not isinstance(self.max_wall_seconds, (int, float)) or not math.isfinite(self.max_wall_seconds) or self.max_wall_seconds <= 0:
            raise ValueError("max_wall_seconds must be finite and positive")
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int) or self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        for name in ("max_provider_calls", "max_bytes", "max_experiments", "max_concurrency"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
                raise ValueError(f"{name} must be positive when supplied")


StageRunner = Callable[..., Mapping[str, str]]
RequestResolver = Callable[[str], ResearchRequest]
TaskResolver = Callable[[str], AgentTask]


class ResearchRuntimeService:
    """Submit and resume bounded, trusted research workflows."""

    DEFAULT_STAGES = ("workflow",)

    def __init__(
        self,
        queue: JobQueue | str | Path,
        *,
        stage_runners: Mapping[str, StageRunner] | None = None,
        request_resolver: RequestResolver | None = None,
        task_resolver: TaskResolver | None = None,
        orchestrator: ResearchOrchestrator | None = None,
        driver: Any | None = None,
        tools: Any | None = None,
        worker_id: str = "research-runtime",
        timeout_seconds: float = 60.0,
        max_result_bytes: int = 8192,
        max_attempts: int = 8,
    ) -> None:
        self.queue = queue if isinstance(queue, JobQueue) else JobQueue(queue, max_attempts=max_attempts, backoff_base_seconds=0)
        self._request_resolver = request_resolver
        self._external_task_resolver = task_resolver
        self._requests: dict[str, ResearchRequest] = {}
        self._orchestrator = orchestrator or ResearchOrchestrator()
        self._driver = driver or OfflineDriver()
        self._tools = tools or ResearchToolGateway()
        supplied = dict(stage_runners or {})
        if not supplied:
            supplied = {"workflow": self._default_workflow_stage}
        if not supplied or any(not isinstance(name, str) or not name.strip() or not callable(runner) for name, runner in supplied.items()):
            raise ValueError("stage_runners must contain trusted callables")
        self._stage_runners = {name.strip(): runner for name, runner in supplied.items()}
        self._worker_id = _ref(worker_id, "worker_id")
        self._run_lock = threading.Lock()
        self._active_runs = 0
        self._active_budget: RuntimeBudget | None = None
        self._last_metrics: RuntimeMetrics | None = None
        self._timeout_seconds = float(timeout_seconds)
        self._max_result_bytes = int(max_result_bytes)
        if not math.isfinite(self._timeout_seconds) or self._timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be finite and positive")
        if self._max_result_bytes < 1:
            raise ValueError("max_result_bytes must be positive")

    @staticmethod
    def _task_ref(request: ResearchRequest) -> str:
        return f"runtime-{stable_digest(request)[:32]}"

    @staticmethod
    def _idempotency_key(request: ResearchRequest) -> str:
        return f"runtime:{stable_digest(request)[:40]}"

    def submit(self, request: ResearchRequest, idempotency_key: str | None = None) -> JobRecord:
        if not isinstance(request, ResearchRequest):
            raise TypeError("request must be ResearchRequest")
        task_ref = self._task_ref(request)
        task = AgentTask(
            role="research_runtime",
            task_id=task_ref,
            input_digest=stable_digest(request),
            capabilities=("paper_only", "durable_checkpoint"),
            inputs={"request_ref": f"request:{stable_digest(request)[:32]}"},
            timeout_seconds=self._timeout_seconds,
        )
        record = self.queue.enqueue(task, idempotency_key or self._idempotency_key(request))
        self._requests[task_ref] = request
        return record

    def cancel(self, job_id: str) -> JobRecord:
        return self.queue.cancel(job_id)

    def run_until_terminal(self, job_id: str, limits: RuntimeLimits | Any | None = None) -> WorkerResult:
        bounds = self._limits(limits)
        with self._run_lock:
            if self._active_runs >= bounds.max_concurrency:
                return self._resource_limit(job_id)
            self._active_runs += 1
        try:
            return self._run_bounded(job_id, bounds)
        finally:
            with self._run_lock:
                self._active_runs -= 1
                self._active_budget = None

    def _run_bounded(self, job_id: str, bounds: RuntimeLimits) -> WorkerResult:
        started = time.monotonic()
        self._active_budget = RuntimeBudget(job_id, bounds)
        worker = self._worker(max_jobs=bounds.max_attempts, timeout_seconds=min(self._timeout_seconds, bounds.max_wall_seconds), max_result_bytes=min(self._max_result_bytes, bounds.max_bytes) if bounds.max_bytes is not None else self._max_result_bytes)
        calls = 0
        while time.monotonic() - started < bounds.max_wall_seconds and calls < bounds.max_attempts:
            record = self.queue.get(job_id)
            terminal = self._terminal_result(record)
            if terminal is not None:
                return terminal
            result = worker.run_once(target_job_id=job_id)
            calls += 1
            if self._active_budget is not None:
                self._active_budget.retry_count = max(0, calls - 1)
                self._last_metrics = self._active_budget.metrics()
            record = self.queue.get(job_id)
            if result.status in {WorkerStatus.COMPLETED, WorkerStatus.FAILED, WorkerStatus.CANCELLED}:
                return result
            terminal = self._terminal_result(record)
            if terminal is not None:
                return terminal
            if result.status is WorkerStatus.IDLE:
                delay = max(0.0, min(0.05, record.available_at - time.time()))
                if delay:
                    time.sleep(delay)
                else:
                    time.sleep(0.005)
        return self._resource_limit(job_id)

    def _resource_limit(self, job_id: str) -> WorkerResult:
        return WorkerResult(WorkerStatus.RETRYABLE, job_id, failure_kind="RESOURCE_LIMIT", message_digest=stable_digest("RESOURCE_LIMIT"), attempts=self.queue.get(job_id).attempts)

    @property
    def metrics(self) -> RuntimeMetrics | None:
        return self._last_metrics

    def resume(self, job_id: str) -> WorkerResult:
        record = self.queue.get(job_id)
        terminal = self._terminal_result(record)
        if terminal is not None:
            return terminal
        return self.run_until_terminal(job_id, RuntimeLimits(max_wall_seconds=self._timeout_seconds * 2, max_attempts=self.queue.max_attempts))

    def _limits(self, limits: RuntimeLimits | Any | None) -> RuntimeLimits:
        if limits is None:
            return RuntimeLimits(max_wall_seconds=max(1.0, self._timeout_seconds * 2), max_attempts=self.queue.max_attempts)
        if isinstance(limits, RuntimeLimits):
            return limits
        return RuntimeLimits(
            max_wall_seconds=float(getattr(limits, "max_wall_seconds", self._timeout_seconds * 2)),
            max_attempts=int(getattr(limits, "max_attempts", self.queue.max_attempts)),
            max_provider_calls=getattr(limits, "max_provider_calls", None),
            max_bytes=getattr(limits, "max_bytes", None),
            max_experiments=getattr(limits, "max_experiments", None),
            max_concurrency=getattr(limits, "max_concurrency", 1),
        )

    def _worker(self, *, max_jobs: int, timeout_seconds: float | None = None, max_result_bytes: int | None = None) -> ResearchWorker:
        return ResearchWorker(
            self.queue,
            runner=self._trusted_runner,
            worker_id=self._worker_id,
            task_resolver=self._resolve_task,
            timeout_seconds=timeout_seconds or self._timeout_seconds,
            max_result_bytes=max_result_bytes or self._max_result_bytes,
            max_jobs=max_jobs,
        )

    def _resolve_task(self, task_ref: str) -> AgentTask:
        if self._external_task_resolver is not None:
            task = self._external_task_resolver(task_ref)
            if not isinstance(task, AgentTask):
                raise TypeError("task resolver must return AgentTask")
            return task
        request = self._resolve_request(task_ref)
        timeout = self.queue.task_timeout(task_ref)
        return AgentTask(
            role="research_runtime",
            task_id=task_ref,
            input_digest=stable_digest(request),
            capabilities=("paper_only", "durable_checkpoint"),
            inputs={"request_ref": f"request:{stable_digest(request)[:32]}"},
            timeout_seconds=timeout,
        )

    def _resolve_request(self, task_ref: str) -> ResearchRequest:
        request = self._requests.get(task_ref)
        if request is None and self._request_resolver is not None:
            request = self._request_resolver(task_ref)
            if not isinstance(request, ResearchRequest):
                raise TypeError("request resolver must return ResearchRequest")
            self._requests[task_ref] = request
        if request is None:
            raise KeyError("request resolver is required after restart")
        return request

    def _trusted_runner(self, task: AgentTask, checkpoint_ref: str | None, publish_checkpoint: Callable[[str], None] | None = None) -> Mapping[str, str]:
        request = self._resolve_request(task.task_id)
        job = self.queue.job_for_task(task.task_id)
        completed = {str(item["stage_name"]): str(item["result_ref"]) for item in self.queue.stage_checkpoints(job.job_id) if item["status"] == "completed" and item["result_ref"]}
        previous = dict(completed)
        latest = checkpoint_ref
        for stage_name, runner in self._stage_runners.items():
            if stage_name in completed:
                continue
            if self.queue.is_cancel_requested(job.job_id):
                return {"failure": "CANCELLED"}
            try:
                budget = self._active_budget
                if budget is not None:
                    budget.check_wall()
                    stage_started = time.monotonic()
                    with bind_runtime_budget(budget):
                        value = self._invoke_stage(runner, request, previous, publish_checkpoint)
                    budget.record_stage_duration(stage_name, time.monotonic() - stage_started)
                    budget.check_wall()
                else:
                    value = self._invoke_stage(runner, request, previous, publish_checkpoint)
                if not isinstance(value, Mapping):
                    raise ValueError("stage result is invalid")
                if value.get("status", "completed") != "completed":
                    raise ValueError("required stage failed")
                raw_ref = value.get("result_ref")
                generated = stable_digest({"stage": stage_name, "request": request, "previous": previous})[:40]
                result_ref = _ref(raw_ref or f"artifact:{generated}", "result_ref")
            except RuntimeLimitExceeded:
                return {"failure": "RESOURCE_LIMIT"}
            except ProviderAdapterError as error:
                return {"failure": "RESOURCE_LIMIT" if error.kind is ProviderFailureKind.RESOURCE_LIMIT else "STAGE_FAILED"}
            except Exception:  # noqa: BLE001 - stage details never cross the worker boundary
                return {"failure": "STAGE_FAILED"}
            stage_ref = f"stage:{stable_digest({'job': job.job_id, 'stage': stage_name, 'result': result_ref})[:40]}"
            try:
                self.queue.record_stage_checkpoint(
                    job.job_id,
                    stage_name,
                    stage_ref,
                    result_ref=result_ref,
                    worker_id=job.worker_id,
                    attempt=job.attempts,
                    lease_until=job.lease_until,
                    lease_token=job.lease_token,
                )
                latest = f"checkpoint:{stable_digest({'job': job.job_id, 'stage': stage_name})[:40]}"
                if publish_checkpoint is not None:
                    publish_checkpoint(latest)
            except Exception:  # noqa: BLE001 - durable publication failure is fail-closed
                return {"failure": "CHECKPOINT_FAILED"}
            previous[stage_name] = result_ref
        final_ref = f"artifact:{stable_digest(previous)[:40]}"
        result: dict[str, str] = {"status": "completed", "result_ref": final_ref}
        if latest is not None:
            result["checkpoint_ref"] = latest
        return result

    @staticmethod
    def _invoke_stage(runner: StageRunner, request: ResearchRequest, previous: Mapping[str, str], publish_checkpoint: Callable[[str], None] | None) -> Mapping[str, str]:
        try:
            signature = inspect.signature(runner)
            positional = [parameter for parameter in signature.parameters.values() if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)]
            variadic = any(parameter.kind is parameter.VAR_POSITIONAL for parameter in signature.parameters.values())
        except (TypeError, ValueError):
            positional, variadic = (), False
        if variadic or len(positional) >= 3:
            return runner(request, dict(previous), publish_checkpoint)
        if len(positional) >= 2:
            return runner(request, dict(previous))
        return runner(request)

    def _default_workflow_stage(self, request: ResearchRequest, previous: Mapping[str, str]) -> Mapping[str, str]:
        del previous
        workflow = self._orchestrator.run(request, self._driver, self._tools)
        return {"status": "completed", "result_ref": f"artifact:{stable_digest(workflow)[:40]}"}

    @staticmethod
    def _terminal_result(record: JobRecord) -> WorkerResult | None:
        mapping = {
            JobStatus.COMPLETED: WorkerStatus.COMPLETED,
            JobStatus.FAILED: WorkerStatus.FAILED,
            JobStatus.CANCELLED: WorkerStatus.CANCELLED,
        }
        status = mapping.get(record.status)
        if status is None:
            return None
        return WorkerResult(status, record.job_id, record.result_ref, failure_kind=record.last_error_digest, attempts=record.attempts, checkpoint_ref=record.checkpoint_ref)


__all__ = ["ResearchRuntimeService", "RuntimeLimits"]
