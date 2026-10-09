from __future__ import annotations

import threading
import multiprocessing
import time

import pytest

from finahinking.research.observability import RuntimeBudget, RuntimeLimitExceeded, bind_runtime_budget
from finahinking.research.provider_adapters import OpenAICompatibleAdapter, ProviderFailureKind, RetryPolicy
from finahinking.research.providers import ModelEnvelope
from finahinking.research.runtime_service import ResearchRuntimeService, RuntimeLimits
from finahinking.research.worker import WorkerStatus

from .test_runtime_service import request


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


def test_service_rejects_concurrent_run_for_same_instance(tmp_path) -> None:
    entered = multiprocessing.get_context("fork").Event()
    release = multiprocessing.get_context("fork").Event()

    def stage(*args):
        entered.set()
        release.wait(1)
        return {"status": "completed", "result_ref": "artifact:done"}

    service = ResearchRuntimeService(tmp_path / "jobs.sqlite", stage_runners={"workflow": stage})
    first = service.submit(request("limit-concurrency-1"))
    second = service.submit(request("limit-concurrency-2"))
    thread = threading.Thread(target=lambda: service.run_until_terminal(first.job_id, RuntimeLimits(max_concurrency=1)))
    thread.start()
    assert entered.wait(2)
    try:
        result = service.run_until_terminal(second.job_id, RuntimeLimits(max_concurrency=1))
        assert result.status is WorkerStatus.RETRYABLE
        assert result.failure_kind == "RESOURCE_LIMIT"
    finally:
        release.set()
        thread.join(3)
