"""Small, strict, JSON-only protocol used by spawned research workers."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

ALLOWED_MESSAGE_KINDS = frozenset(
    {"READY", "CHECKPOINT", "PROGRESS", "RESULT", "FAILED", "CANCELLED", "HEARTBEAT"}
)
_INVOCATION_FIELDS = frozenset(
    {"job_id", "task_ref", "task_digest", "checkpoint_ref", "stage_names", "timeout_seconds", "max_result_bytes", "budget"}
)
_MESSAGE_FIELDS = frozenset({"kind", "job_id", "payload"})
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_UNSAFE_KEY_RE = re.compile(
    r"(?:^|[_-])(secret|token|password|credential|endpoint|prompt|path|api[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)
_UNSAFE_VALUE_RE = re.compile(
    r"(?:^/|^\\|^[A-Za-z]:[\\/]|^(?:https?|file|ftp)://|\b(?:prompt|api[_-]?key|secret|token|password|credential)\b\s*[:=]?)",
    re.IGNORECASE,
)


class ProtocolError(ValueError):
    """Raised when an IPC value does not satisfy the runtime protocol."""


def _finite_number(value: object, name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProtocolError(f"{name} must be a finite number")
    return value


def _safe_json(value: object, *, name: str = "payload") -> object:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if _UNSAFE_VALUE_RE.search(value):
            raise ProtocolError(f"{name} contains an unsafe value")
        return value
    if isinstance(value, (int, float)):
        return _finite_number(value, name)
    if isinstance(value, (list, tuple)):
        return [_safe_json(item, name=name) for item in value]
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or _UNSAFE_KEY_RE.search(key):
                raise ProtocolError(f"{name} contains an unsafe field")
            result[key] = _safe_json(item, name=f"{name}.{key}")
        return result
    raise ProtocolError(f"{name} contains a non-JSON value")


def _freeze_json(value: object, *, name: str = "payload") -> object:
    """Validate and recursively copy JSON values into immutable containers."""

    safe = _safe_json(value, name=name)
    if isinstance(safe, dict):
        return MappingProxyType({key: _freeze_json(item, name=f"{name}.{key}") for key, item in safe.items()})
    if isinstance(safe, list):
        return tuple(_freeze_json(item, name=name) for item in safe)
    return safe


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class WorkerInvocation:
    job_id: str
    task_ref: str
    task_digest: str
    checkpoint_ref: str | None
    stage_names: tuple[str, ...]
    timeout_seconds: float
    max_result_bytes: int
    budget: Mapping[str, int | float | None]

    def __post_init__(self) -> None:
        if not isinstance(self.job_id, str) or not isinstance(self.task_ref, str) or not isinstance(self.task_digest, str):
            raise ProtocolError("invocation references must be strings")
        if not isinstance(self.stage_names, (tuple, list)):
            raise ProtocolError("stage_names must be a tuple or list")
        if not isinstance(self.budget, Mapping):
            raise ProtocolError("budget must be a mapping")
        payload = {
            "job_id": self.job_id,
            "task_ref": self.task_ref,
            "task_digest": self.task_digest,
            "checkpoint_ref": self.checkpoint_ref,
            "stage_names": list(self.stage_names),
            "timeout_seconds": self.timeout_seconds,
            "max_result_bytes": self.max_result_bytes,
            "budget": dict(self.budget),
        }
        self._validate_payload(payload)
        object.__setattr__(self, "stage_names", tuple(self.stage_names))
        object.__setattr__(self, "budget", MappingProxyType(dict(self.budget)))

    @staticmethod
    def _validate_payload(payload: Mapping[str, object]) -> None:
        if set(payload) != _INVOCATION_FIELDS:
            raise ProtocolError("invocation fields are not exact")
        for field in ("job_id", "task_ref", "task_digest"):
            if not isinstance(payload[field], str) or not payload[field].strip():
                raise ProtocolError(f"{field} must be a non-empty string")
            _safe_json(payload[field], name=field)
        if not _DIGEST_RE.fullmatch(payload["task_digest"]):
            raise ProtocolError("task_digest must be a SHA-256 hex digest")
        checkpoint = payload["checkpoint_ref"]
        if checkpoint is not None and (not isinstance(checkpoint, str) or not checkpoint.strip()):
            raise ProtocolError("checkpoint_ref must be a string or null")
        if checkpoint is not None:
            _safe_json(checkpoint, name="checkpoint_ref")
        stages = payload["stage_names"]
        if not isinstance(stages, (list, tuple)) or any(not isinstance(stage, str) or not stage for stage in stages):
            raise ProtocolError("stage_names must contain only non-empty strings")
        for stage in stages:
            _safe_json(stage, name="stage_names")
        timeout = _finite_number(payload["timeout_seconds"], "timeout_seconds")
        if timeout <= 0:
            raise ProtocolError("timeout_seconds must be positive")
        max_bytes = payload["max_result_bytes"]
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise ProtocolError("max_result_bytes must be a positive integer")
        budget = payload["budget"]
        if not isinstance(budget, Mapping) or any(not isinstance(key, str) or not key for key in budget):
            raise ProtocolError("budget must be a mapping")
        for key, value in budget.items():
            if re.search(r"(?:secret|password|credential|api[_-]?key|prompt|path)", key, re.IGNORECASE):
                raise ProtocolError("budget contains an unsafe field")
            if value is not None:
                _finite_number(value, f"budget.{key}")

    def to_payload(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "task_ref": self.task_ref,
            "task_digest": self.task_digest,
            "checkpoint_ref": self.checkpoint_ref,
            "stage_names": list(self.stage_names),
            "timeout_seconds": self.timeout_seconds,
            "max_result_bytes": self.max_result_bytes,
            "budget": dict(self.budget),
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> WorkerInvocation:
        if not isinstance(payload, Mapping) or set(payload) != _INVOCATION_FIELDS:
            raise ProtocolError("invocation fields are not exact")
        cls._validate_payload(payload)
        return cls(
            job_id=payload["job_id"], task_ref=payload["task_ref"], task_digest=payload["task_digest"],
            checkpoint_ref=payload["checkpoint_ref"], stage_names=tuple(payload["stage_names"]),
            timeout_seconds=payload["timeout_seconds"], max_result_bytes=payload["max_result_bytes"], budget=dict(payload["budget"]),
        )

    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_payload())).hexdigest()


@dataclass(frozen=True)
class WorkerMessage:
    kind: str
    job_id: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if self.kind not in ALLOWED_MESSAGE_KINDS:
            raise ProtocolError("unknown message kind")
        if not isinstance(self.job_id, str) or not self.job_id.strip():
            raise ProtocolError("job_id must be a non-empty string")
        if not isinstance(self.payload, Mapping):
            raise ProtocolError("payload must be a mapping")
        if "job_id" in self.payload and self.payload["job_id"] != self.job_id:
            raise ProtocolError("message job_id mismatch")
        digest = self.payload.get("invocation_digest")
        if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
            raise ProtocolError("message invocation_digest is required")
        allowed = _MESSAGE_PAYLOAD_FIELDS[self.kind]
        if not set(self.payload).issubset(allowed):
            raise ProtocolError("message payload contains unknown fields")
        frozen = _freeze_json(dict(self.payload))
        object.__setattr__(self, "payload", frozen)

    def validate_for(self, invocation: WorkerInvocation) -> WorkerMessage:
        if not isinstance(invocation, WorkerInvocation):
            raise ProtocolError("invocation must be WorkerInvocation")
        if self.job_id != invocation.job_id or self.payload.get("job_id", self.job_id) != invocation.job_id:
            raise ProtocolError("message does not match invocation job_id")
        if self.payload["invocation_digest"] != invocation.digest():
            raise ProtocolError("message invocation_digest does not match invocation")
        return self


_MESSAGE_PAYLOAD_FIELDS: dict[str, frozenset[str]] = {
        kind: frozenset({"invocation_digest", "job_id", "attempt", "sequence", "status"})
    for kind in ("READY", "HEARTBEAT", "CANCELLED")
}
_MESSAGE_PAYLOAD_FIELDS.update(
    {
        "CHECKPOINT": frozenset({"invocation_digest", "job_id", "attempt", "sequence", "status", "stage_name", "checkpoint_ref"}),
        "PROGRESS": frozenset({"invocation_digest", "job_id", "attempt", "sequence", "status", "stage_name", "metrics", "progress"}),
        "RESULT": frozenset({"invocation_digest", "job_id", "attempt", "sequence", "status", "result_ref", "artifact_digest", "metrics", "value"}),
        "FAILED": frozenset({"invocation_digest", "job_id", "attempt", "sequence", "status", "failure_kind", "error_code", "message_digest"}),
    }
)


def encode_message(message: WorkerMessage, max_bytes: int) -> bytes:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ProtocolError("max_bytes must be positive")
    if not isinstance(message, WorkerMessage):
        raise ProtocolError("message must be WorkerMessage")
    raw = _canonical({"kind": message.kind, "job_id": message.job_id, "payload": _safe_json(message.payload)})
    if len(raw) > max_bytes:
        raise ProtocolError("message exceeds max_bytes")
    return raw


def decode_message(raw: bytes, max_bytes: int, *, expected_invocation_digest: str | None = None) -> WorkerMessage:
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ProtocolError("max_bytes must be positive")
    if not isinstance(raw, bytes) or len(raw) > max_bytes:
        raise ProtocolError("message exceeds max_bytes")
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON field")
            value[key] = item
        return value

    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
            object_pairs_hook=reject_duplicates,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ProtocolError("message is not valid JSON") from exc
    if not isinstance(value, Mapping) or set(value) != _MESSAGE_FIELDS:
        raise ProtocolError("message envelope fields are not exact")
    message = WorkerMessage(value["kind"], value["job_id"], value["payload"])
    if expected_invocation_digest is not None and (
        not _DIGEST_RE.fullmatch(expected_invocation_digest) or message.payload["invocation_digest"] != expected_invocation_digest
    ):
        raise ProtocolError("message invocation_digest does not match expected digest")
    return message
