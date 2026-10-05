"""Immutable, JSON-safe contracts for the governed research workflow.

This module intentionally contains no model SDK, network client, filesystem
writer, or execution side effect.  It is the shared vocabulary between the
offline engine, optional model drivers, reports, learning, and the UI.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ResearchState(str, Enum):
    RECEIVED = "RECEIVED"
    IDENTIFIED = "IDENTIFIED"
    DATA_CHECKED = "DATA_CHECKED"
    ANALYSTS_RUNNING = "ANALYSTS_RUNNING"
    ANALYSTS_READY = "ANALYSTS_READY"
    EVIDENCE_REVIEW = "EVIDENCE_REVIEW"
    RESEARCH_PLAN_READY = "RESEARCH_PLAN_READY"
    QUANT_VALIDATION = "QUANT_VALIDATION"
    RISK_REVIEW = "RISK_REVIEW"
    PAPER_DECISION_READY = "PAPER_DECISION_READY"
    REPORT_PUBLISHED = "REPORT_PUBLISHED"
    LEARNING_RECORDED = "LEARNING_RECORDED"
    REJECTED = "REJECTED"
    NO_DATA_AVAILABLE = "NO_DATA_AVAILABLE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class FailureKind(str, Enum):
    NO_DATA_AVAILABLE = "NO_DATA_AVAILABLE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    DATA_INVALID = "DATA_INVALID"
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    TOOL_REJECTED = "TOOL_REJECTED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    ANALYST_REQUIRED_MISSING = "ANALYST_REQUIRED_MISSING"
    ANALYST_OPTIONAL_FAILURE = "ANALYST_OPTIONAL_FAILURE"
    ANALYST_TIMEOUT = "ANALYST_TIMEOUT"
    QUANT_VALIDATION_FAILED = "QUANT_VALIDATION_FAILED"
    RISK_REVIEW_FAILED = "RISK_REVIEW_FAILED"
    CANCELLED = "CANCELLED"


_TERMINAL_STATES = frozenset(
    {
        ResearchState.LEARNING_RECORDED,
        ResearchState.REJECTED,
        ResearchState.NO_DATA_AVAILABLE,
        ResearchState.DATA_UNAVAILABLE,
        ResearchState.VALIDATION_FAILED,
        ResearchState.PROVIDER_NOT_CONFIGURED,
        ResearchState.CANCELLED,
        ResearchState.FAILED,
    }
)

_TRANSITIONS: dict[ResearchState, frozenset[ResearchState]] = {
    ResearchState.RECEIVED: frozenset({ResearchState.IDENTIFIED, ResearchState.REJECTED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.IDENTIFIED: frozenset({ResearchState.DATA_CHECKED, ResearchState.REJECTED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.DATA_CHECKED: frozenset({ResearchState.ANALYSTS_RUNNING, ResearchState.NO_DATA_AVAILABLE, ResearchState.DATA_UNAVAILABLE, ResearchState.VALIDATION_FAILED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.ANALYSTS_RUNNING: frozenset({ResearchState.ANALYSTS_READY, ResearchState.PROVIDER_NOT_CONFIGURED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.ANALYSTS_READY: frozenset({ResearchState.EVIDENCE_REVIEW, ResearchState.VALIDATION_FAILED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.EVIDENCE_REVIEW: frozenset({ResearchState.RESEARCH_PLAN_READY, ResearchState.VALIDATION_FAILED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.RESEARCH_PLAN_READY: frozenset({ResearchState.QUANT_VALIDATION, ResearchState.VALIDATION_FAILED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.QUANT_VALIDATION: frozenset({ResearchState.RISK_REVIEW, ResearchState.VALIDATION_FAILED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.RISK_REVIEW: frozenset({ResearchState.PAPER_DECISION_READY, ResearchState.VALIDATION_FAILED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.PAPER_DECISION_READY: frozenset({ResearchState.REPORT_PUBLISHED, ResearchState.CANCELLED, ResearchState.FAILED}),
    ResearchState.REPORT_PUBLISHED: frozenset({ResearchState.LEARNING_RECORDED, ResearchState.CANCELLED, ResearchState.FAILED}),
}

_SECRET_KEY = re.compile(r"(?:api[-_]?key|secret|token|password|credential|authorization)", re.IGNORECASE)
_SENSITIVE_KEY = re.compile(r"(?:endpoint|absolute[-_]?path|file[-_]?path|private[-_]?key)", re.IGNORECASE)


def _nonempty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value.strip()


def _as_date(value: date | str, field_name: str = "as_of") -> date:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO date") from exc
    if not isinstance(value, date):
        raise TypeError(f"{field_name} must be a date")
    return value


def _as_datetime(value: datetime | str | None, field_name: str = "timestamp") -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO datetime") from exc
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _text_tuple(values: Sequence[str], field_name: str, *, unique: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise TypeError(f"{field_name} must be a sequence of strings")
    result = tuple(_nonempty(value, field_name) for value in values)
    if unique and len(result) != len(set(result)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return result


@dataclass(frozen=True, slots=True)
class ResearchPlan:
    hypotheses: tuple[str, ...] = ()
    required_datasets: tuple[str, ...] = ()
    factor_ids: tuple[str, ...] = ()
    validation_spec: Mapping[str, Any] = field(default_factory=dict)
    risk_policy_version: str = "risk.v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "hypotheses", _text_tuple(self.hypotheses, "hypotheses"))
        object.__setattr__(self, "required_datasets", _text_tuple(self.required_datasets, "required_datasets", unique=True))
        object.__setattr__(self, "factor_ids", _text_tuple(self.factor_ids, "factor_ids", unique=True))
        object.__setattr__(self, "risk_policy_version", _nonempty(self.risk_policy_version, "risk_policy_version"))
        object.__setattr__(self, "validation_spec", dict(self.validation_spec))


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    run_id: str
    instrument: str
    as_of: date | str
    research_plan: ResearchPlan | str
    analyst_roles: tuple[str, ...]
    asset_class: str
    workflow_version: str
    config_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _nonempty(self.run_id, "run_id"))
        object.__setattr__(self, "instrument", _nonempty(self.instrument, "instrument"))
        object.__setattr__(self, "as_of", _as_date(self.as_of))
        if not isinstance(self.research_plan, (ResearchPlan, str)):
            raise TypeError("research_plan must be ResearchPlan or string")
        if isinstance(self.research_plan, str):
            object.__setattr__(self, "research_plan", _nonempty(self.research_plan, "research_plan"))
        object.__setattr__(self, "analyst_roles", _text_tuple(self.analyst_roles, "analyst_roles", unique=True))
        object.__setattr__(self, "asset_class", _nonempty(self.asset_class, "asset_class"))
        object.__setattr__(self, "workflow_version", _nonempty(self.workflow_version, "workflow_version"))
        object.__setattr__(self, "config_digest", _nonempty(self.config_digest, "config_digest"))


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    provider: str
    model: str
    role_models: Mapping[str, str] = field(default_factory=dict)
    capabilities: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", _nonempty(self.provider, "provider"))
        object.__setattr__(self, "model", _nonempty(self.model, "model"))
        object.__setattr__(self, "role_models", dict(self.role_models))
        object.__setattr__(self, "capabilities", _text_tuple(self.capabilities, "capabilities", unique=True))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def redacted(self) -> dict[str, Any]:
        def scrub(value: Any) -> Any:
            if isinstance(value, Mapping):
                return {
                    str(key): scrub(item)
                    for key, item in value.items()
                    if not _SECRET_KEY.search(str(key)) and not _SENSITIVE_KEY.search(str(key))
                }
            if isinstance(value, (list, tuple)):
                return [scrub(item) for item in value]
            return value

        return scrub(
            {
                "provider": self.provider,
                "model": self.model,
                "role_models": self.role_models,
                "capabilities": self.capabilities,
                "metadata": self.metadata,
            }
        )


@dataclass(frozen=True, slots=True)
class AgentReport:
    role: str
    status: str
    claims: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    model_ref: str = "offline"
    finished_at: datetime | str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "role", _nonempty(self.role, "role"))
        object.__setattr__(self, "status", _nonempty(self.status, "status"))
        object.__setattr__(self, "claims", _text_tuple(self.claims, "claims"))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs", unique=True))
        object.__setattr__(self, "limitations", _text_tuple(self.limitations, "limitations"))
        object.__setattr__(self, "model_ref", _nonempty(self.model_ref, "model_ref"))
        object.__setattr__(self, "finished_at", _as_datetime(self.finished_at, "finished_at"))


@dataclass(frozen=True, slots=True)
class RiskReview:
    status: str
    gates: tuple[str, ...] = ()
    rationale: str = ""
    blocking_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "status", _nonempty(self.status, "status"))
        object.__setattr__(self, "gates", _text_tuple(self.gates, "gates"))
        object.__setattr__(self, "rationale", self.rationale.strip())
        object.__setattr__(self, "blocking_reasons", _text_tuple(self.blocking_reasons, "blocking_reasons"))


@dataclass(frozen=True, slots=True)
class DecisionCard:
    action: str
    weights: Mapping[str, float]
    rationale: str
    evidence_refs: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    approval_required: bool = True
    eligible: bool = False
    paper_only: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", _nonempty(self.action, "action"))
        object.__setattr__(self, "weights", dict(self.weights))
        object.__setattr__(self, "rationale", _nonempty(self.rationale, "rationale"))
        object.__setattr__(self, "evidence_refs", _text_tuple(self.evidence_refs, "evidence_refs", unique=True))
        object.__setattr__(self, "limitations", _text_tuple(self.limitations, "limitations"))


@dataclass(frozen=True, slots=True)
class RunEvent:
    event_id: str
    run_id: str
    state: ResearchState
    actor: str
    timestamp: datetime | str
    payload_digest: str
    severity: str = "INFO"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_id", _nonempty(self.event_id, "event_id"))
        object.__setattr__(self, "run_id", _nonempty(self.run_id, "run_id"))
        if not isinstance(self.state, ResearchState):
            object.__setattr__(self, "state", ResearchState(self.state))
        object.__setattr__(self, "actor", _nonempty(self.actor, "actor"))
        timestamp = _as_datetime(self.timestamp)
        if timestamp is None:
            raise ValueError("timestamp must be set")
        object.__setattr__(self, "timestamp", timestamp)
        object.__setattr__(self, "payload_digest", _nonempty(self.payload_digest, "payload_digest"))
        object.__setattr__(self, "severity", _nonempty(self.severity, "severity").upper())
        object.__setattr__(self, "metadata", dict(self.metadata))


@dataclass(frozen=True, slots=True)
class ResearchRunState:
    run_id: str
    current_state: ResearchState
    as_of: date | str | None = None
    state_history: tuple[ResearchState, ...] = ()
    analyst_reports: tuple[AgentReport, ...] = ()
    failure_kind: FailureKind | None = None
    failure_message: str | None = None
    decision_eligible: bool = False
    tool_call_digests: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _nonempty(self.run_id, "run_id"))
        if not isinstance(self.current_state, ResearchState):
            object.__setattr__(self, "current_state", ResearchState(self.current_state))
        if self.as_of is not None:
            object.__setattr__(self, "as_of", _as_date(self.as_of))
        history = tuple(ResearchState(item) for item in self.state_history) or (self.current_state,)
        object.__setattr__(self, "state_history", history)
        object.__setattr__(self, "analyst_reports", tuple(self.analyst_reports))
        if self.failure_kind is not None and not isinstance(self.failure_kind, FailureKind):
            object.__setattr__(self, "failure_kind", FailureKind(self.failure_kind))
        if self.failure_message is not None:
            object.__setattr__(self, "failure_message", self.failure_message.strip())
        object.__setattr__(self, "tool_call_digests", _text_tuple(self.tool_call_digests, "tool_call_digests", unique=True))


@dataclass(frozen=True, slots=True)
class CheckpointIdentity:
    instrument: str
    as_of: date | str
    dataset_snapshot: Mapping[str, Any]
    analyst_set: tuple[str, ...]
    role_model_map: Mapping[str, str]
    skill_versions: Mapping[str, str]
    workflow_version: str
    depth: int
    rounds: int
    config_digest: str
    research_plan_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument", _nonempty(self.instrument, "instrument"))
        object.__setattr__(self, "as_of", _as_date(self.as_of))
        snapshot = dict(self.dataset_snapshot)
        snapshot_as_of = snapshot.get("as_of")
        if snapshot_as_of is not None and _as_date(snapshot_as_of, "dataset_snapshot.as_of") > self.as_of:
            raise ValueError("dataset_snapshot.as_of cannot be after as_of")
        object.__setattr__(self, "dataset_snapshot", snapshot)
        object.__setattr__(self, "analyst_set", _text_tuple(self.analyst_set, "analyst_set", unique=True))
        object.__setattr__(self, "role_model_map", dict(self.role_model_map))
        object.__setattr__(self, "skill_versions", dict(self.skill_versions))
        object.__setattr__(self, "workflow_version", _nonempty(self.workflow_version, "workflow_version"))
        if not isinstance(self.depth, int) or self.depth < 0:
            raise ValueError("depth must be a non-negative integer")
        if not isinstance(self.rounds, int) or self.rounds < 0:
            raise ValueError("rounds must be a non-negative integer")
        object.__setattr__(self, "config_digest", _nonempty(self.config_digest, "config_digest"))
        object.__setattr__(self, "research_plan_digest", _nonempty(self.research_plan_digest, "research_plan_digest"))

    def digest(self) -> str:
        return stable_digest(self)


@dataclass(frozen=True, slots=True)
class ReportManifest:
    run_id: str
    schema_version: str
    files: Mapping[str, str]
    source_snapshot: Mapping[str, Any]
    created_at: datetime | str

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _nonempty(self.run_id, "run_id"))
        object.__setattr__(self, "schema_version", _nonempty(self.schema_version, "schema_version"))
        object.__setattr__(self, "files", dict(self.files))
        object.__setattr__(self, "source_snapshot", dict(self.source_snapshot))
        timestamp = _as_datetime(self.created_at, "created_at")
        if timestamp is None:
            raise ValueError("created_at must be set")
        object.__setattr__(self, "created_at", timestamp)


@dataclass(frozen=True, slots=True)
class ResearchRunResult:
    state: ResearchRunState
    events: tuple[RunEvent, ...] = ()
    decision: DecisionCard | None = None
    manifest: ReportManifest | None = None


def validate_transition(previous: ResearchState | str, current: ResearchState | str) -> None:
    previous_state = ResearchState(previous)
    current_state = ResearchState(current)
    if previous_state in _TERMINAL_STATES:
        raise ValueError(f"terminal state {previous_state.value} cannot transition")
    if current_state not in _TRANSITIONS.get(previous_state, frozenset()):
        raise ValueError(f"invalid transition {previous_state.value} -> {current_state.value}")


def _key_is_sensitive(key: str) -> bool:
    return bool(_SECRET_KEY.search(key) or _SENSITIVE_KEY.search(key))


def to_jsonable(value: Any) -> Any:
    """Convert only the contract's safe value types to canonical JSON values."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        raise TypeError("Path values are not allowed in contracts")
    if callable(value):
        raise TypeError("callable values are not allowed in contracts")
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise TypeError("bytes values are not allowed in contracts")
    if is_dataclass(value):
        return {
            item.name: to_jsonable(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("mapping keys must be strings")
            if _key_is_sensitive(key):
                raise ValueError(f"secret or sensitive key is not allowed: {key}")
            result[key] = to_jsonable(item)
        return {key: result[key] for key in sorted(result)}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        raise TypeError("set values are not allowed because ordering is unstable")
    raise TypeError(f"unsupported contract value: {type(value).__name__}")


def stable_digest(value: Any) -> str:
    encoded = json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
