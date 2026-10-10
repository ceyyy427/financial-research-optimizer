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
    {
        "job_id",
        "task_ref",
        "task_digest",
        "checkpoint_ref",
        "stage_names",
        "timeout_seconds",
        "max_result_bytes",
        "budget",
    }
)
_MESSAGE_FIELDS = frozenset({"kind", "job_id", "payload"})
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_REF = re.compile(
    r"(?:^|[_\W])(?:api[-_]?key|secret|token|password|credential(?:s)?|authorization|prompt|endpoint|"
    r"path|absolute[-_]?path|file[-_]?path|private[-_]?key|raw(?:[-_]?provider)?[-_]?response|"
    r"provider[-_]?response)(?=$|[_\W])",
    re.IGNORECASE,
)
_URI_VALUE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://", re.IGNORECASE)
_PATH_VALUE = re.compile(
    r"(?:^|[:\s])(?:[A-Za-z]:[\\/]|~[\\/]|[\\/]|\.{1,2}[\\/]|[A-Za-z0-9_.-]+[\\/])|\\",
    re.IGNORECASE,
)
_UNSAFE_VALUE_RE = re.compile(
    r"(?:^|[_\W])(?:api[-_]?key|secret|token|password|credential(?:s)?|authorization|prompt|endpoint|"
    r"path|absolute[-_]?path|file[-_]?path|private[-_]?key|raw(?:[-_]?provider)?[-_]?response|"
    r"provider[-_]?response)(?=$|[_\W])",
    re.IGNORECASE,
)
_MAX_JSON_DEPTH = 32
_MAX_INVOCATION_BYTES = 65_536


class ProtocolError(ValueError):
    """Raised when an IPC value does not satisfy the runtime protocol."""


def _finite_number(value: object, name: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ProtocolError(f"{name} must be a finite number")
    return value


def _check_string(value: str, name: str) -> str:
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ProtocolError(f"{name} contains an invalid surrogate")
    if _URI_VALUE.search(value) or _PATH_VALUE.search(value) or _UNSAFE_VALUE_RE.search(value):
        raise ProtocolError(f"{name} contains an unsafe value")
    return value


def _safe_json(value: object, *, name: str = "payload", depth: int = 0) -> object:
    """Validate and copy JSON-compatible data with bounded nesting."""

    if depth > _MAX_JSON_DEPTH:
        raise ProtocolError(f"{name} exceeds maximum JSON depth")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _check_string(value, name)
    if isinstance(value, (int, float)):
        return _finite_number(value, name)
    if isinstance(value, (list, tuple)):
        return [_safe_json(item, name=f"{name}[{index}]", depth=depth + 1) for index, item in enumerate(value)]
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or _SENSITIVE_REF.search(key):
                raise ProtocolError(f"{name} contains an unsafe field")
            _check_string(key, f"{name} field")
            result[key] = _safe_json(item, name=f"{name}.{key}", depth=depth + 1)
        return result
    raise ProtocolError(f"{name} contains a non-JSON value")


def _freeze_json(value: object, *, name: str = "payload", depth: int = 0) -> object:
    """Validate and recursively copy JSON values into immutable containers."""

    if depth > _MAX_JSON_DEPTH:
        raise ProtocolError(f"{name} exceeds maximum JSON depth")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        return _check_string(value, name)
    if isinstance(value, (int, float)):
        return _finite_number(value, name)
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(item, name=f"{name}[{index}]", depth=depth + 1)
            for index, item in enumerate(value)
        )
    if isinstance(value, Mapping):
        frozen: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or _SENSITIVE_REF.search(key):
                raise ProtocolError(f"{name} contains an unsafe field")
            _check_string(key, f"{name} field")
            frozen[key] = _freeze_json(item, name=f"{name}.{key}", depth=depth + 1)
        return MappingProxyType(frozen)
    raise ProtocolError(f"{name} contains a non-JSON value")


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise ProtocolError("value cannot be encoded as canonical JSON") from exc


def _public_ref(value: object, name: str, *, allow_none: bool = False) -> str | None:
    if value is None and allow_none:
        return None
    if not isinstance(value, str) or not value.strip() or not _PUBLIC_REF.fullmatch(value):
        raise ProtocolError(f"{name} must be a stable public reference")
    if _SENSITIVE_REF.search(value):
        raise ProtocolError(f"{name} contains an unsafe value")
    _check_string(value, name)
    return value


def _digest(value: object, name: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ProtocolError(f"{name} must be a SHA-256 hex digest")
    return value


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProtocolError(f"{name} must be a non-negative integer")
    return value


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
        encoded = _canonical(_safe_json(payload, name="invocation"))
        if len(encoded) > _MAX_INVOCATION_BYTES:
            raise ProtocolError("invocation exceeds maximum size")
        object.__setattr__(self, "stage_names", tuple(self.stage_names))
        object.__setattr__(self, "budget", MappingProxyType(dict(self.budget)))

    @staticmethod
    def _validate_payload(payload: Mapping[str, object]) -> None:
        if set(payload) != _INVOCATION_FIELDS:
            raise ProtocolError("invocation fields are not exact")
        _public_ref(payload["job_id"], "job_id")
        _public_ref(payload["task_ref"], "task_ref")
        _digest(payload["task_digest"], "task_digest")
        _public_ref(payload["checkpoint_ref"], "checkpoint_ref", allow_none=True)
        stages = payload["stage_names"]
        if not isinstance(stages, (list, tuple)):
            raise ProtocolError("stage_names must contain only non-empty strings")
        for index, stage in enumerate(stages):
            _public_ref(stage, f"stage_names[{index}]")
        timeout = _finite_number(payload["timeout_seconds"], "timeout_seconds")
        if timeout <= 0:
            raise ProtocolError("timeout_seconds must be positive")
        max_bytes = payload["max_result_bytes"]
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
            raise ProtocolError("max_result_bytes must be a positive integer")
        budget = payload["budget"]
        if not isinstance(budget, Mapping):
            raise ProtocolError("budget must be a mapping")
        for key, value in budget.items():
            _public_ref(key, f"budget.{key}")
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
            job_id=payload["job_id"],
            task_ref=payload["task_ref"],
            task_digest=payload["task_digest"],
            checkpoint_ref=payload["checkpoint_ref"],
            stage_names=tuple(payload["stage_names"]),
            timeout_seconds=payload["timeout_seconds"],
            max_result_bytes=payload["max_result_bytes"],
            budget=dict(payload["budget"]),
        )

    def digest(self) -> str:
        return hashlib.sha256(_canonical(self.to_payload())).hexdigest()


_MESSAGE_PAYLOAD_FIELDS: dict[str, frozenset[str]] = {
    kind: frozenset({"invocation_digest", "job_id", "attempt", "sequence", "status"})
    for kind in ("READY", "HEARTBEAT", "CANCELLED")
}
_MESSAGE_PAYLOAD_FIELDS.update(
    {
        "CHECKPOINT": frozenset(
            {"invocation_digest", "job_id", "attempt", "sequence", "status", "stage_name", "checkpoint_ref"}
        ),
        "PROGRESS": frozenset(
            {"invocation_digest", "job_id", "attempt", "sequence", "status", "stage_name", "metrics", "progress"}
        ),
        "RESULT": frozenset(
            {
                "invocation_digest",
                "job_id",
                "attempt",
                "sequence",
                "status",
                "result_ref",
                "artifact_digest",
                "metrics",
                "value",
            }
        ),
        "FAILED": frozenset(
            {
                "invocation_digest",
                "job_id",
                "attempt",
                "sequence",
                "status",
                "failure_kind",
                "error_code",
                "message_digest",
            }
        ),
    }
)
_MESSAGE_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "CHECKPOINT": frozenset({"stage_name", "checkpoint_ref"}),
    "PROGRESS": frozenset({"stage_name", "progress"}),
    "FAILED": frozenset({"failure_kind", "error_code", "message_digest"}),
}


@dataclass(frozen=True)
class WorkerMessage:
    kind: str
    job_id: str
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.kind, str) or self.kind not in ALLOWED_MESSAGE_KINDS:
            raise ProtocolError("unknown message kind")
        _public_ref(self.job_id, "job_id")
        if not isinstance(self.payload, Mapping):
            raise ProtocolError("payload must be a mapping")
        if "job_id" in self.payload:
            supplied_job_id = _public_ref(self.payload["job_id"], "payload.job_id")
            if supplied_job_id != self.job_id:
                raise ProtocolError("message job_id mismatch")
        digest = self.payload.get("invocation_digest")
        _digest(digest, "message invocation_digest")
        allowed = _MESSAGE_PAYLOAD_FIELDS[self.kind]
        if not set(self.payload).issubset(allowed):
            raise ProtocolError("message payload contains unknown fields")
        required = _MESSAGE_REQUIRED_FIELDS.get(self.kind, frozenset())
        if not required.issubset(self.payload):
            raise ProtocolError("message payload is missing required fields")
        self._validate_typed_payload()
        object.__setattr__(self, "payload", _freeze_json(dict(self.payload)))

    def _validate_typed_payload(self) -> None:
        payload = self.payload
        for field in ("attempt", "sequence"):
            if field in payload:
                _nonnegative_int(payload[field], f"message {field}")
        if "status" in payload:
            _public_ref(payload["status"], "message status")
        if "stage_name" in payload:
            _public_ref(payload["stage_name"], "message stage_name")
        if "checkpoint_ref" in payload:
            _public_ref(payload["checkpoint_ref"], "message checkpoint_ref")
        if "progress" in payload:
            progress = _finite_number(payload["progress"], "message progress")
            if not 0 <= progress <= 1:
                raise ProtocolError("message progress must be between zero and one")
        if "metrics" in payload and not isinstance(payload["metrics"], Mapping):
            raise ProtocolError("message metrics must be a mapping")
        if "result_ref" in payload:
            _public_ref(payload["result_ref"], "message result_ref")
        if "artifact_digest" in payload:
            _digest(payload["artifact_digest"], "message artifact_digest")
        for field in ("failure_kind", "error_code"):
            if field in payload:
                _public_ref(payload[field], f"message {field}")
        if "message_digest" in payload:
            _digest(payload["message_digest"], "message message_digest")

    def validate_for(self, invocation: WorkerInvocation) -> WorkerMessage:
        if not isinstance(invocation, WorkerInvocation):
            raise ProtocolError("invocation must be WorkerInvocation")
        if self.job_id != invocation.job_id or self.payload.get("job_id", self.job_id) != invocation.job_id:
            raise ProtocolError("message does not match invocation job_id")
        if self.payload["invocation_digest"] != invocation.digest():
            raise ProtocolError("message invocation_digest does not match invocation")
        return self


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
    if expected_invocation_digest is not None:
        _digest(expected_invocation_digest, "expected invocation digest")
        if message.payload["invocation_digest"] != expected_invocation_digest:
            raise ProtocolError("message invocation_digest does not match expected digest")
    return message
