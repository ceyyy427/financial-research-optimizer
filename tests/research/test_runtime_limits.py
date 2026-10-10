from __future__ import annotations

import multiprocessing
import threading
import time

import pytest

from finahinking.research.observability import (
    RuntimeBudget,
    RuntimeLimitExceeded,
    WorkerMetricsDelta,
    bind_runtime_budget,
)
from finahinking.research.provider_adapters import (
    OpenAICompatibleAdapter,
    ProviderFailureKind,
    RetryPolicy,
)
from finahinking.research.providers import ModelEnvelope
from finahinking.research.runtime_service import ResearchRuntimeService, RuntimeLimits
from finahinking.research.worker import WorkerStatus

from .test_runtime_service import request, spawn_stage


def _envelope() -> ModelEnvelope:
    return ModelEnvelope(request_id="run-safe", role="technical", input_digest="input", context_digest="context")


def test_budget_rejects_excess_provider_calls_and_bytes_without_raw_payload() -> None:
    budget = RuntimeBudget("run-safe", RuntimeLimits(max_provider_calls=1, max_bytes=12))
    budget.charge_provider_call(10)
    with pytest.raises(RuntimeLimitExceeded, match="RESOURCE_LIMIT"):
        budget.charge_provider_call(1)
    snapshot = budget.metrics().to_dict()
    assert snapshot["provider_calls"] == 1
    assert snapshot["resource_failures"] == 1
    assert "run-safe" not in str(snapshot)


def test_provider_adapter_stops_retry_before_second_transport_call() -> None:
    calls = []

    def transport(*args, **kwargs):
        calls.append(1)
        return {"status": 500, "json": {}}

    adapter = OpenAICompatibleAdapter(model="fixture", endpoint="https://example.test", transport=transport, retry_policy=RetryPolicy(max_attempts=3))
    budget = RuntimeBudget("run-safe", RuntimeLimits(max_provider_calls=1))
    with bind_runtime_budget(budget), pytest.raises(Exception) as caught:
        adapter.invoke(_envelope())
    assert getattr(caught.value, "kind", None) == ProviderFailureKind.RESOURCE_LIMIT
    assert calls == [1]


def test_experiment_and_wall_limits_are_traceable() -> None:
    budget = RuntimeBudget("run-safe", RuntimeLimits(max_experiments=1, max_wall_seconds=0.01))
    budget.charge_experiments(1)
    with pytest.raises(RuntimeLimitExceeded, match="RESOURCE_LIMIT"):
        budget.charge_experiments(1)
    time.sleep(0.02)
    with pytest.raises(RuntimeLimitExceeded, match="RESOURCE_LIMIT"):
        budget.check_wall()


def test_worker_metrics_deltas_are_aggregated_per_job_and_enforce_limits() -> None:
    limits = RuntimeLimits(max_provider_calls=2, max_bytes=20, max_experiments=3)
    first = RuntimeBudget("job-one", limits)
    second = RuntimeBudget("job-two", limits)
    first.apply_delta(WorkerMetricsDelta("job-one", experiments=2, provider_calls=1, bytes_used=8, stage_seconds={"workflow": 0.5}))
    second.apply_delta(WorkerMetricsDelta("job-two", experiments=1, provider_calls=2, bytes_used=12))
    assert first.metrics().experiments == 2
    assert second.metrics().experiments == 1
    assert first.metrics().stage_durations == {"workflow": 0.5}
    with pytest.raises(RuntimeLimitExceeded, match="RESOURCE_LIMIT"):
        first.apply_delta(WorkerMetricsDelta("job-one", provider_calls=2))
    with pytest.raises(ValueError, match="another job"):
        first.apply_delta(WorkerMetricsDelta("job-two", provider_calls=1))


def test_worker_local_delta_drains_only_unpublished_charges() -> None:
    worker = RuntimeBudget("job-one", RuntimeLimits())
    aggregate = RuntimeBudget("job-one", RuntimeLimits())
    worker.charge_experiments(2)
    worker.charge_provider_call(10)
    aggregate.apply_delta(worker.delta())
    aggregate.apply_delta(worker.delta())
    worker.charge_bytes(5)
    aggregate.apply_delta(worker.delta())
    assert aggregate.metrics().experiments == 2
    assert aggregate.metrics().provider_calls == 1
    assert aggregate.metrics().bytes_used == 15


@pytest.mark.parametrize("amount", [-1, True, 1.5])
def test_provider_charge_cannot_reduce_or_coerce_byte_counter(amount) -> None:
    budget = RuntimeBudget("job-one", RuntimeLimits(max_bytes=1))
    with pytest.raises(ValueError, match="non-negative"):
        budget.charge_provider_call(amount)
    assert budget.metrics().provider_calls == 0
    assert budget.metrics().bytes_used == 0


def test_service_rejects_concurrent_run_for_same_instance(tmp_path) -> None:
    entered = threading.Event()
    release = threading.Event()

    service = ResearchRuntimeService(tmp_path / "jobs.sqlite", stage_runners={"workflow": spawn_stage})
    first = service.submit(request("limit-concurrency-1"))
    second = service.submit(request("limit-concurrency-2"))
    thread = threading.Thread(target=lambda: service.run_until_terminal(first.job_id, RuntimeLimits(max_concurrency=1)))
    thread.start()
    entered.set()
    try:
        result = service.run_until_terminal(second.job_id, RuntimeLimits(max_concurrency=1))
        assert result.status is WorkerStatus.RETRYABLE
        assert result.failure_kind == "RESOURCE_LIMIT"
    finally:
        release.set()
        thread.join(3)


def test_concurrent_runs_keep_independent_budgets_and_metrics(tmp_path) -> None:
    service = ResearchRuntimeService(tmp_path / "jobs.sqlite", stage_runners={"workflow": spawn_stage})
    first = service.submit(request("parallel-1"))
    second = service.submit(request("parallel-2"))
    limits = RuntimeLimits(max_wall_seconds=5, max_attempts=2, max_experiments=1, max_concurrency=2)
    results = {}

    def run(job):
        results[job.job_id] = service.run_until_terminal(job.job_id, limits)

    workers = [threading.Thread(target=run, args=(job,)) for job in (first, second)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(8)
    assert {result.status for result in results.values()} == {WorkerStatus.COMPLETED}
    assert service.metrics_for(first.job_id).retry_count >= 0
    assert service.metrics_for(second.job_id).retry_count >= 0


def test_runtime_service_never_requests_fork_for_worker_creation(tmp_path, monkeypatch) -> None:
    original = multiprocessing.get_context

    def guarded(method="spawn"):
        if method == "fork":
            raise AssertionError("request runtime must not use fork")
        return original(method)

    monkeypatch.setattr(multiprocessing, "get_context", guarded)
    service = ResearchRuntimeService(tmp_path / "jobs.sqlite")
    assert service._supervisor is not None
    service.stop_supervisor()
