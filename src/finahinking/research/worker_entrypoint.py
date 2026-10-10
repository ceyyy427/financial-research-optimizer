"""Spawn-only research worker entrypoint and its parent-side handle.

The process boundary carries a JSON-shaped invocation and a registry bootstrap
descriptor.  The descriptor is produced by a trusted :class:`StageRegistry`
and is checked against its digest before any stage is resolved.  No queue,
request object, runner callable, database handle, or task supplied import path
is sent to the child.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
import math
import multiprocessing
import time
from collections.abc import Callable, Mapping
from multiprocessing.connection import Connection

from .runtime_protocol import (
    ProtocolError,
    WorkerInvocation,
    WorkerMessage,
    decode_message,
    encode_message,
)
from .stage_registry import StageRegistry, StageRegistryError, StageSpec

_TRANSPORT_MAX_BYTES = 65_536
_ATTEMPT = 1
_INVOCATION_KEY = "invocation"
_REGISTRY_KEY = "registry"
_REGISTRY_FIELDS = frozenset({"digest", "stages"})
_STAGE_FIELDS = frozenset({"name", "version", "runner_key", "paper_only", "runner"})


def _message_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _failure_message(
    invocation: WorkerInvocation | None,
    failure_kind: str,
    error_code: str | None = None,
    *,
    sequence: int = 0,
) -> WorkerMessage:
    if invocation is None:
        job_id = "invalid-job"
        digest = _message_digest("invalid-invocation")
    else:
        job_id = invocation.job_id
        digest = invocation.digest()
    code = error_code or failure_kind
    return WorkerMessage(
        "FAILED",
        job_id,
        {
            "invocation_digest": digest,
            "job_id": job_id,
            "attempt": _ATTEMPT,
            "sequence": sequence,
            "status": "failed",
            "failure_kind": failure_kind,
            "error_code": code,
            "message_digest": _message_digest(f"{failure_kind}:{code}"),
        },
    )


def _cancelled_message(invocation: WorkerInvocation, *, sequence: int = 0) -> WorkerMessage:
    return WorkerMessage(
        "CANCELLED",
        invocation.job_id,
        {
            "invocation_digest": invocation.digest(),
            "job_id": invocation.job_id,
            "attempt": _ATTEMPT,
            "sequence": sequence,
            "status": "cancelled",
        },
    )


def _send(connection: Connection, message: WorkerMessage, *, result_limit: int | None = None) -> None:
    """Encode and send one bounded message.

    ``max_result_bytes`` limits the stage result envelope.  Control and
    failure messages use the transport limit so a very small result budget can
    still report an explicit failure kind.
    """

    raw = encode_message(message, _TRANSPORT_MAX_BYTES)
    if result_limit is not None and len(raw) > result_limit:
        raise ProtocolError("result exceeds max_result_bytes")
    connection.send_bytes(raw)


def _registry_payload(registry: StageRegistry) -> dict[str, object]:
    stages: list[dict[str, object]] = []
    for spec in registry.snapshot():
        runner = registry.resolve(spec.name)
        stages.append(
            {
                **spec.to_payload(),
                "runner": {
                    "module": runner.__module__,
                    "name": runner.__name__,
                    "qualname": runner.__qualname__,
                },
            }
        )
    return {"digest": registry.digest(), "stages": stages}


def _registry_descriptor_digest(stages: list[object]) -> str:
    """Hash only the code-owned descriptor, before importing any runner."""

    normalized: list[dict[str, object]] = []
    for item in stages:
        if not isinstance(item, Mapping) or set(item) != _STAGE_FIELDS:
            raise StageRegistryError("registry stage descriptor is malformed")
        runner_identity = item.get("runner")
        if not isinstance(runner_identity, Mapping) or set(runner_identity) != {"module", "name", "qualname"}:
            raise StageRegistryError("registry runner descriptor is malformed")
        module_name = runner_identity.get("module")
        runner_name = runner_identity.get("name")
        qualname = runner_identity.get("qualname")
        if (
            not isinstance(module_name, str)
            or not isinstance(runner_name, str)
            or not isinstance(qualname, str)
            or not module_name
            or not runner_name
            or qualname != runner_name
        ):
            raise StageRegistryError("registry runner identity is malformed")
        spec = StageSpec(
            name=item["name"],
            version=item["version"],
            runner_key=item["runner_key"],
            paper_only=item["paper_only"],
        )
        normalized.append({**spec.to_payload(), "runner": {"module": module_name, "name": runner_name, "qualname": qualname}})
    normalized.sort(key=lambda value: str(value["name"]))
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _rebuild_registry(payload: Mapping[str, object]) -> StageRegistry:
    if not isinstance(payload, Mapping) or set(payload) != _REGISTRY_FIELDS:
        raise StageRegistryError("registry bootstrap is malformed")
    digest = payload.get("digest")
    stages = payload.get("stages")
    if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise StageRegistryError("registry digest is malformed")
    if not isinstance(stages, list):
        raise StageRegistryError("registry stages are malformed")
    # Verify the signed-by-parent descriptor before importing any module name
    # it contains.  The final registry digest check below still confirms that
    # each imported runner is the exact exported top-level callable.
    if _registry_descriptor_digest(stages) != digest:
        raise StageRegistryError("registry digest mismatch")
    registry = StageRegistry()
    for item in stages:
        if not isinstance(item, Mapping) or set(item) != _STAGE_FIELDS:
            raise StageRegistryError("registry stage descriptor is malformed")
        runner_identity = item.get("runner")
        if not isinstance(runner_identity, Mapping) or set(runner_identity) != {"module", "name", "qualname"}:
            raise StageRegistryError("registry runner descriptor is malformed")
        module_name = runner_identity.get("module")
        runner_name = runner_identity.get("name")
        qualname = runner_identity.get("qualname")
        if (
            not isinstance(module_name, str)
            or not isinstance(runner_name, str)
            or not isinstance(qualname, str)
            or qualname != runner_name
            or not module_name
            or not runner_name
        ):
            raise StageRegistryError("registry runner identity is malformed")
        # This import is controlled by the trusted bootstrap descriptor.  The
        # invocation itself cannot provide a module name or callable path.
        module = importlib.import_module(module_name)
        runner = getattr(module, runner_name, None)
        if runner is None:
            raise StageRegistryError("registry runner is unavailable")
        spec = StageSpec(
            name=item["name"],
            version=item["version"],
            runner_key=item["runner_key"],
            paper_only=item["paper_only"],
        )
        registry.register(spec, runner)
    if registry.digest() != digest:
        raise StageRegistryError("registry digest mismatch")
    return registry


def _call_runner(
    runner: Callable[..., Mapping[str, object]],
    invocation: WorkerInvocation,
    checkpoint_ref: str | None,
    publish_checkpoint: Callable[[str], None],
) -> Mapping[str, object]:
    """Call a trusted runner using one of the supported top-level signatures."""

    try:
        signature = inspect.signature(runner)
        parameters = tuple(signature.parameters.values())
    except (TypeError, ValueError) as exc:
        raise TypeError("runner signature is unavailable") from exc
    positional = tuple(
        parameter
        for parameter in parameters
        if parameter.kind in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
    )
    has_varargs = any(parameter.kind is parameter.VAR_POSITIONAL for parameter in parameters)
    has_varkw = any(parameter.kind is parameter.VAR_KEYWORD for parameter in parameters)
    if has_varargs or len(positional) >= 3:
        return runner(invocation, checkpoint_ref, publish_checkpoint)
    if len(positional) >= 2:
        return runner(invocation, checkpoint_ref)
    if len(positional) == 1:
        return runner(invocation)
    if has_varkw:
        return runner(invocation=invocation, checkpoint_ref=checkpoint_ref, publish_checkpoint=publish_checkpoint)
    return runner()


def _result_message(
    invocation: WorkerInvocation,
    stage_result: Mapping[str, object],
    *,
    sequence: int,
) -> WorkerMessage:
    if not isinstance(stage_result, Mapping):
        raise ProtocolError("stage result must be a mapping")
    if stage_result.get("status") != "completed":
        raise ProtocolError("stage did not complete")
    allowed = frozenset({"status", "result_ref", "artifact_digest", "metrics"})
    if set(stage_result) - allowed:
        raise ProtocolError("stage result contains unknown fields")
    if "result_ref" not in stage_result or "artifact_digest" not in stage_result:
        raise ProtocolError("stage result must provide result_ref and artifact_digest")
    payload: dict[str, object] = {
        "invocation_digest": invocation.digest(),
        "job_id": invocation.job_id,
        "attempt": _ATTEMPT,
        "sequence": sequence,
        "status": "completed",
    }
    for key in ("result_ref", "artifact_digest", "metrics"):
        if key in stage_result and stage_result[key] is not None:
            payload[key] = stage_result[key]
    return WorkerMessage("RESULT", invocation.job_id, payload)


def _run_invocation(invocation: WorkerInvocation, registry: StageRegistry, connection: Connection) -> None:
    sequence = 0
    ready = WorkerMessage(
        "READY",
        invocation.job_id,
        {
            "invocation_digest": invocation.digest(),
            "job_id": invocation.job_id,
            "attempt": _ATTEMPT,
            "sequence": sequence,
            "status": "ready",
        },
    )
    _send(connection, ready)
    sequence += 1
    checkpoint_ref = invocation.checkpoint_ref
    final_result: Mapping[str, object] | None = None
    for stage_name in invocation.stage_names:
        try:
            runner = registry.resolve(stage_name)
        except Exception:  # noqa: BLE001 - stage identity is not disclosed
            _send(connection, _failure_message(invocation, "STAGE_UNAVAILABLE", "UNKNOWN_STAGE", sequence=sequence))
            return

        def publish_checkpoint(reference: str, *, _stage_name: str = stage_name) -> None:
            nonlocal sequence
            checkpoint = WorkerMessage(
                "CHECKPOINT",
                invocation.job_id,
                {
                    "invocation_digest": invocation.digest(),
                    "job_id": invocation.job_id,
                    "attempt": _ATTEMPT,
                    "sequence": sequence,
                    "status": "checkpoint",
                    "stage_name": _stage_name,
                    "checkpoint_ref": reference,
                },
            )
            _send(connection, checkpoint)
            sequence += 1

        try:
            final_result = _call_runner(runner, invocation, checkpoint_ref, publish_checkpoint)
        except Exception:  # noqa: BLE001 - runner failures stay opaque
            _send(connection, _failure_message(invocation, "RUNNER_FAILED", "RUNNER_EXCEPTION", sequence=sequence))
            return
        if isinstance(final_result, Mapping) and final_result.get("checkpoint_ref") is not None:
            checkpoint_ref = final_result["checkpoint_ref"]  # type: ignore[assignment]
    if final_result is None:
        _send(connection, _failure_message(invocation, "TASK_CONTRACT_INVALID", "NO_STAGE", sequence=sequence))
        return
    try:
        result = _result_message(invocation, final_result, sequence=sequence)
        _send(connection, result, result_limit=invocation.max_result_bytes)
    except ProtocolError as exc:
        kind = "RESOURCE_LIMIT" if "max_result_bytes" in str(exc).lower() else "RESULT_INVALID"
        _send(connection, _failure_message(invocation, kind, kind, sequence=sequence))


def run_spawn_worker(invocation_payload: Mapping[str, object], connection: Connection) -> None:
    """Top-level spawn target accepting only JSON-shaped values and a pipe."""

    invocation: WorkerInvocation | None = None
    try:
        if not isinstance(invocation_payload, Mapping):
            raise ProtocolError("invocation payload must be a mapping")
        if _INVOCATION_KEY in invocation_payload or _REGISTRY_KEY in invocation_payload:
            if set(invocation_payload) != {_INVOCATION_KEY, _REGISTRY_KEY}:
                raise ProtocolError("spawn payload fields are not exact")
            raw_invocation = invocation_payload[_INVOCATION_KEY]
            registry = _rebuild_registry(invocation_payload[_REGISTRY_KEY])
        else:
            raw_invocation = invocation_payload
            registry = StageRegistry()
        invocation = WorkerInvocation.from_payload(raw_invocation)
        if not registry.snapshot():
            # Direct entrypoint calls can use the built-in registry without
            # exposing a dynamic module path.  Handles always send a registry.
            from .stage_registry import default_stage_registry

            registry = default_stage_registry()
        _run_invocation(invocation, registry, connection)
    except StageRegistryError as exc:
        message = _failure_message(invocation, "STAGE_UNAVAILABLE", "UNKNOWN_STAGE")
        if "registry" in str(exc).lower():
            message = _failure_message(invocation, "TASK_CONTRACT_INVALID", "REGISTRY_INVALID")
        try:
            _send(connection, message)
        except Exception:  # noqa: BLE001 - malformed input must not escape child
            return
    except ProtocolError as exc:
        kind = "RESOURCE_LIMIT" if "result" in str(exc).lower() else "TASK_CONTRACT_INVALID"
        try:
            _send(connection, _failure_message(invocation, kind, kind))
        except Exception:  # noqa: BLE001 - malformed input must not escape child
            return
    except Exception:  # noqa: BLE001 - runner and import failures are opaque
        try:
            _send(connection, _failure_message(invocation, "RUNNER_FAILED", "RUNNER_EXCEPTION"))
        except Exception:  # noqa: BLE001 - malformed input must not escape child
            return
    finally:
        try:
            connection.close()
        except Exception:  # noqa: BLE001 - cleanup is best effort
            return


class SpawnWorkerHandle:
    """Parent-side lifecycle for one spawn worker."""

    def __init__(self, invocation: WorkerInvocation, *, registry: StageRegistry, daemon: bool = True) -> None:
        if not isinstance(invocation, WorkerInvocation):
            raise TypeError("invocation must be WorkerInvocation")
        if not isinstance(registry, StageRegistry):
            raise TypeError("registry must be StageRegistry")
        self.invocation = invocation
        self.registry = registry
        self.daemon = daemon
        self._context = multiprocessing.get_context("spawn")
        self._process: multiprocessing.Process | None = None
        self._connection: Connection | None = None
        self._started_at: float | None = None
        self._next_sequence = 0
        self._terminal: WorkerMessage | None = None
        self._terminal_delivered = False
        self._closed = False

    @property
    def process(self) -> multiprocessing.Process | None:
        return self._process

    def start(self) -> None:
        if self._process is not None:
            raise RuntimeError("worker has already started")
        # Resolve all names before spawning so unknown stages fail in the
        # supervisor process and no child can receive an untrusted callable.
        for stage_name in self.invocation.stage_names:
            self.registry.resolve(stage_name)
        parent, child = self._context.Pipe(duplex=False)
        payload = {
            _INVOCATION_KEY: self.invocation.to_payload(),
            _REGISTRY_KEY: _registry_payload(self.registry),
        }
        process = self._context.Process(target=run_spawn_worker, args=(payload, child), daemon=self.daemon)
        try:
            process.start()
        except Exception:
            child.close()
            parent.close()
            raise
        child.close()
        self._connection = parent
        self._process = process
        self._started_at = time.monotonic()

    def _make_terminal(self, kind: str, code: str) -> WorkerMessage:
        if kind == "CANCELLED":
            return _cancelled_message(self.invocation, sequence=self._next_sequence)
        return _failure_message(self.invocation, kind, code, sequence=self._next_sequence)

    def _terminate(self) -> None:
        process = self._process
        if process is None:
            return
        if process.is_alive():
            process.terminate()
        process.join(timeout=1)
        if process.is_alive():
            process.kill()
            process.join(timeout=1)

    def poll(self, timeout: float) -> WorkerMessage | None:
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
            raise ValueError("timeout must be a finite non-negative number")
        if self._terminal is not None:
            if self._terminal_delivered:
                return None
            self._terminal_delivered = True
            return self._terminal
        if self._closed or self._process is None or self._connection is None:
            return None
        started = self._started_at or time.monotonic()
        remaining = self.invocation.timeout_seconds - (time.monotonic() - started)
        if remaining <= 0:
            self._terminate()
            self._terminal = self._make_terminal("FAILED", "TIMEOUT")
            return self.poll(0)
        if not self._connection.poll(min(float(timeout), remaining)):
            if not self._process.is_alive() and not self._connection.poll(0):
                self._terminal = self._make_terminal("FAILED", "RUNNER_FAILED")
                return self.poll(0)
            if time.monotonic() - started >= self.invocation.timeout_seconds:
                self._terminate()
                self._terminal = self._make_terminal("FAILED", "TIMEOUT")
                return self.poll(0)
            return None
        try:
            raw = self._connection.recv_bytes()
            message = decode_message(raw, _TRANSPORT_MAX_BYTES, expected_invocation_digest=self.invocation.digest())
            message.validate_for(self.invocation)
            attempt = message.payload.get("attempt")
            sequence = message.payload.get("sequence")
            if attempt != _ATTEMPT or sequence != self._next_sequence:
                raise ProtocolError("message attempt or sequence identity mismatch")
            self._next_sequence += 1
            return message
        except (EOFError, OSError, ProtocolError, UnicodeError, ValueError):
            self._terminate()
            self._terminal = self._make_terminal("FAILED", "PROTOCOL_VIOLATION")
            return self.poll(0)

    def cancel(self) -> None:
        if self._terminal is not None:
            return
        self._terminate()
        self._terminal = self._make_terminal("CANCELLED", "CANCELLED")

    def join(self) -> None:
        if self._process is not None:
            self._process.join(timeout=1)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1)
        if self._connection is not None:
            try:
                self._connection.close()
            except OSError:
                pass
        self._closed = True


__all__ = ["SpawnWorkerHandle", "run_spawn_worker"]
