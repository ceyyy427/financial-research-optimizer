"""Focused acceptance tests for the spawn-only worker boundary."""

from __future__ import annotations

import hashlib
import multiprocessing
import time

import pytest

from finahinking.research.runtime_protocol import WorkerInvocation, decode_message
from finahinking.research.stage_registry import StageRegistry, StageRegistryError, StageSpec
from finahinking.research.worker_entrypoint import SpawnWorkerHandle


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def stage_ok(invocation: WorkerInvocation) -> dict[str, object]:
    return {"status": "completed", "result_ref": "artifact:ok", "artifact_digest": _digest("artifact:ok")}


def stage_slow(invocation: WorkerInvocation) -> dict[str, object]:
    time.sleep(2)
    return {"status": "completed", "result_ref": "artifact:late", "artifact_digest": _digest("artifact:late")}


def stage_raises(invocation: WorkerInvocation) -> dict[str, object]:
    raise RuntimeError("opaque")


def stage_invalid_result(invocation: WorkerInvocation) -> dict[str, object]:
    return {"status": "completed", "result_ref": "artifact:missing-digest"}


def _registry(name: str, runner) -> StageRegistry:
    registry = StageRegistry()
    registry.register(StageSpec(name=name, version="1", runner_key=f"test.{name}"), runner)
    return registry


def _invocation(stage: str, *, timeout: float = 2.0, max_result_bytes: int = 2048) -> WorkerInvocation:
    return WorkerInvocation(
        job_id="job-1",
        task_ref="task-1",
        task_digest=_digest("task"),
        checkpoint_ref=None,
        stage_names=(stage,),
        timeout_seconds=timeout,
        max_result_bytes=max_result_bytes,
        budget={"steps": 1},
    )


def _collect(handle: SpawnWorkerHandle) -> list:
    messages = []
    try:
        handle.start()
        for _ in range(20):
            message = handle.poll(0.2)
            if message is not None:
                messages.append(message)
                if message.kind in {"RESULT", "FAILED", "CANCELLED"}:
                    break
    finally:
        handle.join()
    return messages


def test_spawn_emits_ready_then_result_with_identity() -> None:
    invocation = _invocation("ok")
    handle = SpawnWorkerHandle(invocation, registry=_registry("ok", stage_ok))
    assert handle._context.get_start_method() == "spawn"
    messages = _collect(handle)
    assert [message.kind for message in messages] == ["READY", "RESULT"]
    assert all(message.payload["invocation_digest"] == invocation.digest() for message in messages)
    assert [message.payload["attempt"] for message in messages] == [1, 1]
    assert [message.payload["sequence"] for message in messages] == [0, 1]


def test_unknown_stage_is_rejected_before_spawn() -> None:
    handle = SpawnWorkerHandle(_invocation("missing"), registry=_registry("ok", stage_ok))
    with pytest.raises(StageRegistryError):
        handle.start()


def test_runner_exception_is_opaque_failure() -> None:
    messages = _collect(SpawnWorkerHandle(_invocation("raises"), registry=_registry("raises", stage_raises)))
    assert messages[-1].kind == "FAILED"
    assert messages[-1].payload["failure_kind"] == "RUNNER_FAILED"
    assert messages[-1].payload["error_code"] == "RUNNER_EXCEPTION"


def test_timeout_terminates_child() -> None:
    messages = _collect(SpawnWorkerHandle(_invocation("slow", timeout=0.1), registry=_registry("slow", stage_slow)))
    assert messages[-1].kind == "FAILED"
    assert messages[-1].payload["error_code"] == "TIMEOUT"


def test_cancel_is_terminal_and_cleanup_is_deterministic() -> None:
    handle = SpawnWorkerHandle(_invocation("slow"), registry=_registry("slow", stage_slow))
    handle.start()
    assert handle.poll(1).kind == "READY"
    handle.cancel()
    message = handle.poll(0)
    assert message is not None and message.kind == "CANCELLED"
    handle.join()
    assert handle.process is not None and not handle.process.is_alive()


def test_small_result_budget_fails_closed() -> None:
    messages = _collect(SpawnWorkerHandle(_invocation("ok", max_result_bytes=1), registry=_registry("ok", stage_ok)))
    assert messages[-1].kind == "FAILED"
    assert messages[-1].payload["failure_kind"] == "RESOURCE_LIMIT"


def test_invalid_result_contract_fails_closed() -> None:
    messages = _collect(
        SpawnWorkerHandle(
            _invocation("invalid"),
            registry=_registry("invalid", stage_invalid_result),
        )
    )
    assert messages[-1].kind == "FAILED"
    assert messages[-1].payload["failure_kind"] == "RESULT_INVALID"


def test_malformed_direct_payload_fails_closed() -> None:
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    try:
        from finahinking.research.worker_entrypoint import run_spawn_worker

        run_spawn_worker({"job_id": "not-an-invocation"}, child)
        raw = parent.recv_bytes()
        assert decode_message(raw, 65_536).kind == "FAILED"
    finally:
        parent.close()


def test_registry_digest_is_checked_before_runner_import(monkeypatch: pytest.MonkeyPatch) -> None:
    from finahinking.research import worker_entrypoint

    def forbidden_import(name: str):
        raise AssertionError(f"unexpected import: {name}")

    monkeypatch.setattr(worker_entrypoint.importlib, "import_module", forbidden_import)
    descriptor = {
        "digest": "0" * 64,
        "stages": [
            {
                "name": "json-stage",
                "version": "1",
                "runner_key": "json.stage",
                "paper_only": True,
                "runner": {"module": "json", "name": "dumps", "qualname": "dumps"},
            }
        ],
    }
    with pytest.raises(StageRegistryError, match="digest mismatch"):
        worker_entrypoint._rebuild_registry(descriptor)

