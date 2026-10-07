"""Local, atomic persistence for resumable governed research runs.

The store intentionally persists only the typed research contracts.  It never
receives a prompt, provider response, credential value, or artifact payload.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from .contracts import (
    AgentReport,
    CheckpointIdentity,
    FailureKind,
    ResearchRunState,
    ResearchState,
    RunEvent,
    stable_digest,
    to_jsonable,
)


class RunStoreError(ValueError):
    """Base class for typed checkpoint and event store failures."""


class CheckpointValidationError(RunStoreError):
    """A checkpoint is structurally valid JSON but cannot be accepted."""


class CheckpointIdentityMismatch(CheckpointValidationError):
    """The checkpoint identity differs from the requested run identity."""


class CheckpointIncompatibleError(CheckpointValidationError):
    """The checkpoint schema, workflow, or capability contract is incompatible."""


class CompletedRunError(CheckpointValidationError):
    """A completed run cannot be resumed from a temporary checkpoint."""


class CheckpointCorruptError(RunStoreError):
    """Checkpoint or append-only event data is malformed or unreadable."""


# Compatibility names for callers that distinguish schema and restore errors.
CheckpointSchemaError = CheckpointIncompatibleError
CheckpointRestoreError = CheckpointValidationError
CorruptCheckpointError = CheckpointCorruptError


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    """A decoded checkpoint, useful to callers that need identity metadata."""

    state: ResearchRunState
    identity: CheckpointIdentity
    identity_digest: str
    provider_capability_digest: str


_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_CHECKPOINT_REF = re.compile(r"^checkpoint:[A-Za-z0-9_-]{1,128}$")
_CHECKPOINT_SCHEMA = "research-checkpoint.v1"
_COMPLETED_STATES = frozenset({ResearchState.REPORT_PUBLISHED, ResearchState.LEARNING_RECORDED})
_FORBIDDEN_KEYS = re.compile(
    r"(?:^|_)(?:prompt|raw_provider_response|provider_response|raw_response)(?:$|_)",
    re.IGNORECASE,
)
_FORBIDDEN_TEXT = re.compile(
    r"(?:api[-_]?key|secret|token|password|credential|authorization|\bprompt\b|"
    r"(?:raw[\s_-]*)?provider[\s_-]*response|raw[\s_-]*response|\bendpoint\b|"
    r"absolute[-_ ]path|file[-_ ]path|private[-_ ]key|https?://|"
    r"(?:^|[\s:=])/(?:[^\s/]+/)*[^\s/]+|"
    r"(?:^|[\s:=])(?:\.\.?/)+[^\s]+|"
    r"(?:^|[\s:=])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.[A-Za-z0-9]+(?:$|[\s,:]))",
    re.IGNORECASE,
)
_RELATIVE_PATH = re.compile(
    r"(?:^|[\s:=])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+(?:$|[\s,:])"
)
_CHECKPOINT_FIELDS = frozenset(
    {
        "schema_version",
        "workflow_version",
        "identity_digest",
        "provider_capability_digest",
        "dataset_snapshot_digest",
        "analyst_set_digest",
        "identity",
        "state",
    }
)
_IDENTITY_FIELDS = frozenset(
    {
        "instrument",
        "as_of",
        "dataset_snapshot",
        "analyst_set",
        "role_model_map",
        "skill_versions",
        "workflow_version",
        "depth",
        "rounds",
        "config_digest",
        "research_plan_digest",
    }
)
_STATE_FIELDS = frozenset(
    {
        "run_id",
        "current_state",
        "as_of",
        "state_history",
        "analyst_reports",
        "failure_kind",
        "failure_message",
        "decision_eligible",
        "tool_call_digests",
    }
)
_REPORT_FIELDS = frozenset(
    {"role", "status", "claims", "evidence_refs", "limitations", "model_ref", "finished_at"}
)
_EVENT_FIELDS = frozenset(
    {"event_id", "run_id", "state", "actor", "timestamp", "payload_digest", "severity", "metadata"}
)


def _run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not _SAFE_ID.fullmatch(run_id):
        raise ValueError("run id is invalid")
    return run_id


def _provider_capability_digest(identity: CheckpointIdentity) -> str:
    """Derive a deterministic capability identity from the role/model contract."""

    explicit = getattr(identity, "provider_capability_digest", None)
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    return stable_digest(
        {
            "role_model_map": identity.role_model_map,
            "skill_versions": identity.skill_versions,
        }
    )


def _assert_safe_keys(value: Any, *, path: str = "checkpoint payload") -> None:
    if isinstance(value, str):
        is_model_reference = "model_ref" in path or "role_model_map" in path
        if _FORBIDDEN_TEXT.search(value) or (_RELATIVE_PATH.search(value) and not is_model_reference):
            raise ValueError(f"{path} contains forbidden text")
    elif isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{path} contains a non-string key")
            if _FORBIDDEN_KEYS.search(key):
                raise ValueError(f"{path} contains forbidden field: {key}")
            _assert_safe_keys(item, path=f"{path}.{key}")
    elif isinstance(value, (tuple, list)):
        for index, item in enumerate(value):
            _assert_safe_keys(item, path=f"{path}[{index}]")


def _reject_unknown_fields(value: Mapping[str, Any], allowed: frozenset[str], label: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise CheckpointCorruptError(f"{label} contains unknown fields")


def _decode_report(value: Any) -> AgentReport:
    if not isinstance(value, Mapping):
        raise CheckpointCorruptError("checkpoint analyst report is malformed")
    _reject_unknown_fields(value, _REPORT_FIELDS, "checkpoint analyst report")
    try:
        return AgentReport(
            role=value["role"],
            status=value["status"],
            claims=tuple(value.get("claims", ())),
            evidence_refs=tuple(value.get("evidence_refs", ())),
            limitations=tuple(value.get("limitations", ())),
            model_ref=value.get("model_ref", "offline"),
            finished_at=value.get("finished_at"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckpointCorruptError("checkpoint analyst report is invalid") from exc


def _decode_state(value: Any, run_id: str) -> ResearchRunState:
    if not isinstance(value, Mapping):
        raise CheckpointCorruptError("checkpoint state is malformed")
    _reject_unknown_fields(value, _STATE_FIELDS, "checkpoint state")
    if value.get("run_id") != run_id:
        raise CheckpointIdentityMismatch("checkpoint state run_id does not match path")
    try:
        failure_kind = value.get("failure_kind")
        return ResearchRunState(
            run_id=value["run_id"],
            current_state=ResearchState(value["current_state"]),
            as_of=value.get("as_of"),
            state_history=tuple(ResearchState(item) for item in value.get("state_history", ())),
            analyst_reports=tuple(_decode_report(item) for item in value.get("analyst_reports", ())),
            failure_kind=FailureKind(failure_kind) if failure_kind is not None else None,
            failure_message=value.get("failure_message"),
            decision_eligible=bool(value.get("decision_eligible", False)),
            tool_call_digests=tuple(value.get("tool_call_digests", ())),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckpointCorruptError("checkpoint state is invalid") from exc


def _decode_identity(value: Any) -> CheckpointIdentity:
    if not isinstance(value, Mapping):
        raise CheckpointCorruptError("checkpoint identity is malformed")
    _reject_unknown_fields(value, _IDENTITY_FIELDS, "checkpoint identity")
    try:
        return CheckpointIdentity(
            instrument=value["instrument"],
            as_of=value["as_of"],
            dataset_snapshot=value["dataset_snapshot"],
            analyst_set=tuple(value["analyst_set"]),
            role_model_map=value["role_model_map"],
            skill_versions=value["skill_versions"],
            workflow_version=value["workflow_version"],
            depth=value["depth"],
            rounds=value["rounds"],
            config_digest=value["config_digest"],
            research_plan_digest=value["research_plan_digest"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckpointCorruptError("checkpoint identity is invalid") from exc


def _decode_event(value: Any) -> RunEvent:
    if not isinstance(value, Mapping):
        raise CheckpointCorruptError("event record is malformed")
    _reject_unknown_fields(value, _EVENT_FIELDS, "event record")
    try:
        return RunEvent(
            event_id=value["event_id"],
            run_id=value["run_id"],
            state=ResearchState(value["state"]),
            actor=value["actor"],
            timestamp=value["timestamp"],
            payload_digest=value["payload_digest"],
            severity=value.get("severity", "INFO"),
            metadata=value.get("metadata", {}),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CheckpointCorruptError("event record is invalid") from exc


class ResearchRunStore:
    """Persist run checkpoints and append-only events under a local directory."""

    def __init__(
        self,
        root: str | Path,
        *,
        schema_version: str = _CHECKPOINT_SCHEMA,
        workflow_version: str | None = None,
        provider_capability_digest: str | None = None,
    ) -> None:
        if not isinstance(schema_version, str) or not schema_version.strip():
            raise ValueError("schema_version must be non-empty")
        if workflow_version is not None and (not isinstance(workflow_version, str) or not workflow_version.strip()):
            raise ValueError("workflow_version must be non-empty")
        if provider_capability_digest is not None and (
            not isinstance(provider_capability_digest, str) or not provider_capability_digest.strip()
        ):
            raise ValueError("provider_capability_digest must be non-empty")
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.schema_version = schema_version.strip()
        self.workflow_version = workflow_version.strip() if workflow_version else None
        self.provider_capability_digest = provider_capability_digest.strip() if provider_capability_digest else None
        self._event_lock = Lock()

    def _path(self, run_id: str) -> Path:
        return self.root / f"{_run_id(run_id)}.json"

    @staticmethod
    def checkpoint_reference(run_id: str) -> str:
        """Return the public queue reference for a checkpoint, never its path."""
        return f"checkpoint:{_run_id(run_id)}"

    @staticmethod
    def run_id_from_reference(reference: str) -> str:
        if not isinstance(reference, str) or not _CHECKPOINT_REF.fullmatch(reference):
            raise ValueError("checkpoint reference is invalid")
        return _run_id(reference.split(":", 1)[1])

    def has_checkpoint(self, run_id: str) -> bool:
        return self._path(run_id).is_file()

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    def save_checkpoint(self, state: ResearchRunState, identity: CheckpointIdentity) -> Path:
        if not isinstance(state, ResearchRunState):
            raise TypeError("state must be ResearchRunState")
        if not isinstance(identity, CheckpointIdentity):
            raise TypeError("identity must be CheckpointIdentity")
        if state.current_state in _COMPLETED_STATES:
            raise CompletedRunError("completed run cannot be checkpointed")
        if self.workflow_version is not None and identity.workflow_version != self.workflow_version:
            raise CheckpointIncompatibleError("workflow version is incompatible")
        try:
            state_payload = to_jsonable(state)
            identity_payload = to_jsonable(identity)
            _assert_safe_keys(state_payload)
            _assert_safe_keys(identity_payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"checkpoint payload rejected: {exc}") from exc
        cap_digest = self.provider_capability_digest or _provider_capability_digest(identity)
        envelope = {
            "schema_version": self.schema_version,
            "workflow_version": identity.workflow_version,
            "identity_digest": identity.digest(),
            "provider_capability_digest": cap_digest,
            "dataset_snapshot_digest": stable_digest(identity.dataset_snapshot),
            "analyst_set_digest": stable_digest(identity.analyst_set),
            "identity": identity_payload,
            "state": state_payload,
        }
        _assert_safe_keys(envelope)
        path = self._path(state.run_id)
        _atomic_write(path, _encode(envelope))
        return path

    def load_checkpoint(
        self,
        run_id: str,
        identity: CheckpointIdentity | None = None,
        *,
        expected_identity: CheckpointIdentity | None = None,
        provider_capability_digest: str | None = None,
    ) -> ResearchRunState:
        run_id = _run_id(run_id)
        if identity is not None and expected_identity is not None:
            raise TypeError("provide identity or expected_identity, not both")
        expected = identity or expected_identity
        path = self._path(run_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"checkpoint not found: {run_id}") from exc
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CheckpointCorruptError("checkpoint JSON is corrupt") from exc
        record = self._decode_checkpoint(payload, run_id)
        if expected is not None and record.identity_digest != expected.digest():
            raise CheckpointIdentityMismatch("checkpoint identity does not match requested run")
        if self.workflow_version is not None and record.identity.workflow_version != self.workflow_version:
            raise CheckpointIncompatibleError("workflow version is incompatible")
        if provider_capability_digest is not None and record.provider_capability_digest != provider_capability_digest:
            raise CheckpointIdentityMismatch("provider capability digest does not match")
        expected_capability_digest = self.provider_capability_digest or _provider_capability_digest(record.identity)
        if record.provider_capability_digest != expected_capability_digest:
            raise CheckpointIdentityMismatch("provider capability digest does not match")
        return record.state

    def load_record(
        self,
        run_id: str,
        identity: CheckpointIdentity | None = None,
        *,
        expected_identity: CheckpointIdentity | None = None,
        provider_capability_digest: str | None = None,
    ) -> CheckpointRecord:
        """Load identity metadata as well as state for queue/recovery callers."""

        if identity is not None and expected_identity is not None:
            raise TypeError("provide identity or expected_identity, not both")
        expected = identity or expected_identity
        path = self._path(run_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"checkpoint not found: {run_id}") from exc
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CheckpointCorruptError("checkpoint JSON is corrupt") from exc
        record = self._decode_checkpoint(payload, _run_id(run_id))
        if expected is not None and record.identity_digest != expected.digest():
            raise CheckpointIdentityMismatch("checkpoint identity does not match requested run")
        if self.workflow_version is not None and record.identity.workflow_version != self.workflow_version:
            raise CheckpointIncompatibleError("workflow version is incompatible")
        expected_capability_digest = provider_capability_digest or self.provider_capability_digest or _provider_capability_digest(record.identity)
        if expected_capability_digest is not None and record.provider_capability_digest != expected_capability_digest:
            raise CheckpointIdentityMismatch("provider capability digest does not match")
        return record

    def _decode_checkpoint(self, payload: Any, run_id: str) -> CheckpointRecord:
        if not isinstance(payload, Mapping):
            raise CheckpointCorruptError("checkpoint must be a JSON object")
        _reject_unknown_fields(payload, _CHECKPOINT_FIELDS, "checkpoint")
        try:
            _assert_safe_keys(payload)
        except ValueError as exc:
            raise CheckpointCorruptError("checkpoint contains forbidden fields") from exc
        if payload.get("schema_version") != self.schema_version:
            raise CheckpointIncompatibleError("checkpoint schema version is incompatible")
        try:
            identity = _decode_identity(payload["identity"])
            state = _decode_state(payload["state"], run_id)
        except KeyError as exc:
            raise CheckpointCorruptError("checkpoint is missing a required field") from exc
        if payload.get("identity_digest") != identity.digest():
            raise CheckpointCorruptError("checkpoint identity digest is invalid")
        if payload.get("workflow_version") != identity.workflow_version:
            raise CheckpointIncompatibleError("checkpoint workflow version is inconsistent")
        if payload.get("dataset_snapshot_digest") != stable_digest(identity.dataset_snapshot):
            raise CheckpointIncompatibleError("checkpoint dataset snapshot is inconsistent")
        if payload.get("analyst_set_digest") != stable_digest(identity.analyst_set):
            raise CheckpointIncompatibleError("checkpoint analyst set is inconsistent")
        cap_digest = payload.get("provider_capability_digest")
        if not isinstance(cap_digest, str) or not cap_digest.strip():
            raise CheckpointIncompatibleError("checkpoint provider capability digest is missing")
        if state.current_state in _COMPLETED_STATES:
            raise CompletedRunError("completed run cannot be resumed")
        return CheckpointRecord(state, identity, identity.digest(), cap_digest)

    def clear_checkpoint(self, run_id: str) -> None:
        path = self._path(run_id)
        try:
            path.unlink()
        except FileNotFoundError:
            return

    def append_event(self, event: RunEvent) -> Path:
        if not isinstance(event, RunEvent):
            raise TypeError("event must be RunEvent")
        try:
            payload = to_jsonable(event)
            _assert_safe_keys(payload)
            encoded = _encode(payload)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"event payload rejected: {exc}") from exc
        path = self.events_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._event_lock, path.open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return path

    def read_events(self) -> tuple[RunEvent, ...]:
        path = self.events_path
        if not path.exists():
            return ()
        events: list[RunEvent] = []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise CheckpointCorruptError("event JSONL is unreadable") from exc
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CheckpointCorruptError("event JSONL is corrupt") from exc
            try:
                _assert_safe_keys(payload)
            except ValueError as exc:
                raise CheckpointCorruptError("event JSONL contains forbidden fields") from exc
            events.append(_decode_event(payload))
        return tuple(events)


class RunControl:
    """Process-local cancellation token shared by a bounded workflow run."""

    def __init__(self) -> None:
        self._cancelled: set[str] = set()
        self._lock = Lock()

    def cancel(self, run_id: str) -> bool:
        run_id = _run_id(run_id)
        with self._lock:
            if run_id in self._cancelled:
                return False
            self._cancelled.add(run_id)
            return True

    def is_cancelled(self, run_id: str) -> bool:
        run_id = _run_id(run_id)
        with self._lock:
            return run_id in self._cancelled

    def clear(self, run_id: str) -> None:
        run_id = _run_id(run_id)
        with self._lock:
            self._cancelled.discard(run_id)


def _encode(value: Any) -> str:
    return json.dumps(to_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


__all__ = [
    "CheckpointCorruptError",
    "CheckpointIdentityMismatch",
    "CheckpointIncompatibleError",
    "CheckpointRecord",
    "CheckpointRestoreError",
    "CheckpointSchemaError",
    "CheckpointValidationError",
    "CompletedRunError",
    "CorruptCheckpointError",
    "ResearchRunStore",
    "RunControl",
    "RunStoreError",
]
