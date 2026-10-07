"""Explicit Codex handoff contracts for the offline research runtime.

This module creates an envelope for an external turn; it never calls the
current Codex session and never treats a missing callback as a successful
research outcome.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .contracts import AgentOutcome, stable_digest

_FORBIDDEN_CAPABILITY_PARTS = frozenset(
    {"account", "broker", "call", "cancel", "execute", "filesystem", "live", "network", "order", "shell", "tool", "write"}
)
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "credential",
        "endpoint",
        "file_path",
        "path",
        "password",
        "prompt",
        "raw_provider_object",
        "raw_provider_response",
        "secret",
        "token",
    }
)
_SENSITIVE_TEXT = re.compile(
    r"(?:api[-_]?key|authorization|password|secret|token|https?://|/Users/|/private/|prompt)",
    re.IGNORECASE,
)


def _field(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _nonempty(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")
    return value.strip()


def _capabilities(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("capabilities must be a sequence of strings")
    normalized: list[str] = []
    for item in value:
        if type(item) is not str or not item.strip():
            raise TypeError("capabilities must contain only non-empty strings")
        name = item.strip()
        lowered = name.casefold()
        if any(part in lowered.split("_") for part in _FORBIDDEN_CAPABILITY_PARTS):
            raise ValueError("capability is outside the research boundary")
        normalized.append(name)
    if len(set(normalized)) != len(normalized):
        raise ValueError("capabilities must not contain duplicates")
    return tuple(sorted(normalized))


@dataclass(frozen=True, slots=True)
class CodexTaskEnvelope:
    task_id: str
    role: str
    input_digest: str
    context_digest: str
    prompt_digest: str
    capabilities: tuple[str, ...] = ()
    workflow_version: str = "research.v1"
    schema_version: str = "codex-task.v1"
    paper_only: bool = True
    tool_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("task_id", "role", "input_digest", "context_digest", "prompt_digest", "workflow_version", "schema_version"):
            object.__setattr__(self, name, _nonempty(getattr(self, name), name))
        object.__setattr__(self, "role", self.role.casefold())
        object.__setattr__(self, "capabilities", _capabilities(self.capabilities))
        if self.paper_only is not True:
            raise ValueError("Codex handoff must be paper-only")
        object.__setattr__(self, "tool_names", ())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "role": self.role,
            "input_digest": self.input_digest,
            "context_digest": self.context_digest,
            "prompt_digest": self.prompt_digest,
            "capabilities": list(self.capabilities),
            "workflow_version": self.workflow_version,
            "paper_only": True,
            "tool_names": [],
        }


def _contains_sensitive(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in _SENSITIVE_KEYS:
                return True
            if _contains_sensitive(item):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_sensitive(item) for item in value)
    elif isinstance(value, str):
        return _SENSITIVE_TEXT.search(value) is not None
    return False


class CodexBridge:
    def __init__(self, *, schema_version: str = "codex-task.v1", workflow_version: str = "research.v1") -> None:
        self.schema_version = _nonempty(schema_version, "schema_version")
        self.workflow_version = _nonempty(workflow_version, "workflow_version")
        self._accepted: set[str] = set()

    def create_handoff(self, task: object) -> CodexTaskEnvelope:
        task_id = _nonempty(_field(task, "task_id"), "task_id")
        role = _nonempty(_field(task, "role"), "role").casefold()
        input_digest = _nonempty(_field(task, "input_digest"), "input_digest")
        capabilities = _capabilities(_field(task, "capabilities", ()))
        context_value = _field(task, "context_digest")
        if context_value is None:
            context_value = stable_digest({"task_id": task_id, "role": role, "input_digest": input_digest})
        prompt_value = _field(task, "prompt_digest")
        if prompt_value is None:
            raw_prompt = _field(task, "prompt")
            prompt_value = stable_digest(raw_prompt if raw_prompt is not None else {"task_id": task_id, "role": role})
        return CodexTaskEnvelope(
            task_id=task_id,
            role=role,
            input_digest=input_digest,
            context_digest=_nonempty(context_value, "context_digest"),
            prompt_digest=_nonempty(prompt_value, "prompt_digest"),
            capabilities=capabilities,
            workflow_version=_nonempty(_field(task, "workflow_version", self.workflow_version), "workflow_version"),
            schema_version=self.schema_version,
        )

    def accept_result(self, envelope: CodexTaskEnvelope, result: Mapping[str, Any] | None) -> AgentOutcome:
        if not isinstance(envelope, CodexTaskEnvelope):
            raise TypeError("envelope must be a CodexTaskEnvelope")
        envelope_key = stable_digest(envelope.to_dict())
        if envelope_key in self._accepted:
            return self._outcome(envelope, status="REJECTED", failure_kind="DUPLICATE_RESULT")
        if result is None:
            return self._outcome(envelope, status="EXTERNAL_HANDOFF_REQUIRED", failure_kind="EXTERNAL_HANDOFF_REQUIRED")
        self._accepted.add(envelope_key)
        if not isinstance(result, Mapping):
            return self._outcome(envelope, status="REJECTED", failure_kind="SCHEMA_ERROR")
        if _contains_sensitive(result):
            return self._outcome(envelope, status="REJECTED", failure_kind="ARTIFACT_BOUNDARY_VIOLATION")
        if result.get("schema_version") != envelope.schema_version:
            return self._outcome(envelope, status="REJECTED", failure_kind="SCHEMA_ERROR")
        if result.get("input_digest") != envelope.input_digest:
            return self._outcome(envelope, status="REJECTED", failure_kind="INPUT_DIGEST_MISMATCH")
        if result.get("task_id", envelope.task_id) != envelope.task_id or result.get("role", envelope.role) != envelope.role:
            return self._outcome(envelope, status="REJECTED", failure_kind="SCHEMA_ERROR")
        if result.get("paper_only", True) is not True:
            return self._outcome(envelope, status="REJECTED", failure_kind="PAPER_ONLY_VIOLATION")
        try:
            result_capabilities = _capabilities(result.get("capabilities", envelope.capabilities))
        except (TypeError, ValueError):
            return self._outcome(envelope, status="REJECTED", failure_kind="CAPABILITY_DENIED")
        if not set(result_capabilities).issubset(envelope.capabilities):
            return self._outcome(envelope, status="REJECTED", failure_kind="CAPABILITY_DENIED")
        status = result.get("status", "READY")
        if not isinstance(status, str) or not status.strip():
            return self._outcome(envelope, status="REJECTED", failure_kind="SCHEMA_ERROR")
        failure_kind = result.get("failure_kind")
        if failure_kind is not None and (not isinstance(failure_kind, str) or not failure_kind.strip()):
            return self._outcome(envelope, status="REJECTED", failure_kind="SCHEMA_ERROR")
        refs = result.get("evidence_refs", ())
        if isinstance(refs, (str, bytes)) or not isinstance(refs, Sequence) or any(not isinstance(item, str) or not item.strip() for item in refs):
            return self._outcome(envelope, status="REJECTED", failure_kind="SCHEMA_ERROR")
        return self._outcome(
            envelope,
            status=status,
            failure_kind=failure_kind,
            evidence_refs=tuple(sorted({item.strip() for item in refs})),
            output_digest=stable_digest({"status": status.strip(), "failure_kind": failure_kind, "evidence_refs": tuple(refs)}),
        )

    @staticmethod
    def _outcome(
        envelope: CodexTaskEnvelope,
        *,
        status: str,
        failure_kind: str | None = None,
        evidence_refs: tuple[str, ...] = (),
        output_digest: str = "",
    ) -> AgentOutcome:
        return AgentOutcome(
            role=envelope.role,
            task_id=envelope.task_id,
            input_digest=envelope.input_digest,
            capabilities=envelope.capabilities,
            status=status,
            failure_kind=failure_kind,
            message_digest=stable_digest({"status": status, "failure_kind": failure_kind, "task_id": envelope.task_id}),
            evidence_refs=evidence_refs,
            output_digest=output_digest,
            paper_only=True,
        )


__all__ = ["CodexBridge", "CodexTaskEnvelope"]
