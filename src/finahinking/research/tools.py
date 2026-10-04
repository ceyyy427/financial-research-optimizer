"""Allow-listed typed bridge from research orchestration to Finathink services."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from finahinking.quant.services import QuantServiceGateway, ToolRequest, ToolStatus

from .contracts import FailureKind, stable_digest


class ResearchToolName(str, Enum):
    INSPECT_DATASET = "research.inspect_dataset"
    RESOLVE_INSTRUMENT = "research.resolve_instrument"
    COMPUTE_FACTOR = "research.compute_factor"
    RUN_BACKTEST = "quant.run_backtest"
    RUN_REGRESSION = "quant.run_regression"
    EVALUATE_PERFORMANCE = "quant.evaluate_performance"
    ANALYZE_RISK = "quant.analyze_risk"
    INSPECT_RUN = "quant.inspect_run"
    RENDER_REPORT = "research.render_report"
    INSPECT_ASOF_LESSONS = "learning.inspect_asof_lessons"
    RECORD_EVIDENCE = "learning.record_evidence"


class ResearchToolStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ResearchToolRequest:
    name: ResearchToolName | str
    args: Mapping[str, Any] = field(default_factory=dict)
    run_id: str = ""

    def __post_init__(self) -> None:
        name = self.name.value if isinstance(self.name, ResearchToolName) else str(self.name).strip()
        if not name:
            raise ValueError("tool name is required")
        if not isinstance(self.args, Mapping):
            raise TypeError("args must be a mapping")
        if not isinstance(self.run_id, str) or not self.run_id.strip() or "/" in self.run_id:
            raise ValueError("run_id is required and must not contain slash")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "args", dict(self.args))
        object.__setattr__(self, "run_id", self.run_id.strip())

    @property
    def request_digest(self) -> str:
        return stable_digest({"name": self.name, "args": self.args, "run_id": self.run_id})


@dataclass(frozen=True, slots=True)
class ResearchToolResponse:
    request_id: str
    name: str
    status: ResearchToolStatus
    result: Any = None
    artifact_refs: tuple[str, ...] = ()
    failure_kind: FailureKind | None = None
    provenance: Mapping[str, Any] = field(default_factory=dict)
    request_digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, ResearchToolStatus):
            object.__setattr__(self, "status", ResearchToolStatus(self.status))
        if self.failure_kind is not None and not isinstance(self.failure_kind, FailureKind):
            object.__setattr__(self, "failure_kind", FailureKind(self.failure_kind))
        object.__setattr__(self, "artifact_refs", tuple(self.artifact_refs))
        object.__setattr__(self, "provenance", dict(self.provenance))


_FORBIDDEN_KEYS = {
    "__class__", "__code__", "__globals__", "callable", "command", "eval", "exec",
    "file_path", "import", "imports", "module", "path", "shell", "source", "sql",
    "subprocess", "url", "endpoint", "api_key", "token", "secret",
}
_FORBIDDEN_TEXT = (
    re.compile(r"(?:eval\s*\(|exec\s*\(|__import__|subprocess|os\.system|shell_command)", re.IGNORECASE),
    re.compile(r"\b(?:select|insert|update|delete)\s+.+\s+from\b", re.IGNORECASE),
    re.compile(r"(?:^[~/]|^\.\.?/|^[A-Za-z]:[\\/]|^[A-Za-z][A-Za-z0-9+.-]*://)", re.IGNORECASE),
)
_RESEARCH_ARG_KEYS: dict[str, frozenset[str]] = {
    ResearchToolName.INSPECT_DATASET.value: frozenset({"dataset_id", "fields", "as_of"}),
    ResearchToolName.RESOLVE_INSTRUMENT.value: frozenset({"instrument", "as_of"}),
    ResearchToolName.COMPUTE_FACTOR.value: frozenset({"factor_id", "dataset_id", "as_of"}),
    ResearchToolName.RENDER_REPORT.value: frozenset({"run_id", "section"}),
    ResearchToolName.INSPECT_ASOF_LESSONS.value: frozenset({"as_of", "scope"}),
    ResearchToolName.RECORD_EVIDENCE.value: frozenset({"entry_id", "run_id", "claim", "evidence_refs", "as_of"}),
}


def _unsafe(value: Any) -> bool:
    if callable(value):
        return True
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).casefold() in _FORBIDDEN_KEYS or _unsafe(key) or _unsafe(item):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_unsafe(item) for item in value)
    return isinstance(value, str) and any(pattern.search(value) for pattern in _FORBIDDEN_TEXT)


def validate_tool_args(name: ResearchToolName | str, args: Mapping[str, Any], *, run_id: str, max_args_bytes: int = 65536) -> None:
    tool_name = name.value if isinstance(name, ResearchToolName) else str(name)
    if not isinstance(args, Mapping):
        raise TypeError("tool args must be a mapping")
    if _unsafe(args):
        raise ValueError("tool args contain a forbidden execution directive")
    allowed = _RESEARCH_ARG_KEYS.get(tool_name)
    if allowed is not None:
        unknown = set(args) - allowed
        if unknown:
            raise ValueError(f"unknown tool args: {sorted(unknown)}")
    if "run_id" in args and args["run_id"] != run_id:
        raise ValueError("tool run_id does not match request run_id")
    try:
        encoded = json.dumps(args, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise TypeError("tool args must be bounded JSON data") from exc
    if len(encoded.encode("utf-8")) > max_args_bytes:
        raise ValueError("tool args exceed size limit")


class ResearchToolGateway:
    def __init__(self, *, quant_gateway: QuantServiceGateway | None = None, max_args_bytes: int = 65536) -> None:
        self.quant_gateway = quant_gateway
        self.max_args_bytes = max_args_bytes
        self._cache: dict[str, ResearchToolResponse] = {}

    @property
    def approved_tools(self) -> tuple[str, ...]:
        return tuple(item.value for item in ResearchToolName)

    def execute(self, request: ResearchToolRequest) -> ResearchToolResponse:
        if not isinstance(request, ResearchToolRequest):
            return self._rejected("unknown", "invalid request", request_id="unknown")
        try:
            validate_tool_args(request.name, request.args, run_id=request.run_id, max_args_bytes=self.max_args_bytes)
            digest = request.request_digest
        except (TypeError, ValueError) as exc:
            return self._rejected(request.name, str(exc), request_id=request.run_id)
        if request.name not in self.approved_tools:
            return self._rejected(request.name, "tool is not allow-listed", request_id=request.run_id, digest=digest)
        if digest in self._cache:
            return self._cache[digest]
        if request.name.startswith("quant."):
            response = self._execute_quant(request, digest)
        else:
            response = self._execute_research(request, digest)
        self._cache[digest] = response
        return response

    def _execute_quant(self, request: ResearchToolRequest, digest: str) -> ResearchToolResponse:
        if self.quant_gateway is None:
            return ResearchToolResponse(
                request_id=request.run_id,
                name=request.name,
                status=ResearchToolStatus.UNAVAILABLE,
                failure_kind=FailureKind.DATA_UNAVAILABLE,
                provenance={"gateway": "finahinking-research-v1", "request_digest": digest},
                request_digest=digest,
            )
        try:
            response = self.quant_gateway.execute(
                ToolRequest(request.name, dict(request.args), research_run_id=request.run_id)
            )
        except (TypeError, ValueError) as exc:
            return self._rejected(request.name, str(exc), request_id=request.run_id, digest=digest)
        if response.status is ToolStatus.SUCCEEDED:
            return ResearchToolResponse(
                request_id=response.request_id,
                name=request.name,
                status=ResearchToolStatus.SUCCEEDED,
                result=response.result,
                artifact_refs=tuple(ref for ref in (response.artifact_fingerprint,) if ref),
                provenance={**response.provenance, "gateway": "finahinking-research-v1"},
                request_digest=digest,
            )
        return ResearchToolResponse(
            request_id=response.request_id,
            name=request.name,
            status=ResearchToolStatus.REJECTED if response.status is ToolStatus.REJECTED else ResearchToolStatus.FAILED,
            result=response.result,
            failure_kind=FailureKind.TOOL_REJECTED if response.status is ToolStatus.REJECTED else FailureKind.DATA_UNAVAILABLE,
            provenance={**response.provenance, "gateway": "finahinking-research-v1"},
            request_digest=digest,
        )

    def _execute_research(self, request: ResearchToolRequest, digest: str) -> ResearchToolResponse:
        args = request.args
        if request.name == ResearchToolName.INSPECT_DATASET.value:
            result = {"dataset_id": args.get("dataset_id", "fixture"), "status": "AVAILABLE"}
        elif request.name == ResearchToolName.RESOLVE_INSTRUMENT.value:
            result = {"instrument": args.get("instrument", "unknown"), "resolved": True}
        elif request.name == ResearchToolName.COMPUTE_FACTOR.value:
            result = {"factor_id": args.get("factor_id", "fixture.factor.v1"), "status": "COMPUTED"}
        elif request.name == ResearchToolName.RENDER_REPORT.value:
            result = {"report_ref": f"report:{request.run_id}:{args.get('section', 'complete')}"}
        elif request.name == ResearchToolName.INSPECT_ASOF_LESSONS.value:
            result = {"lessons": [], "as_of": args.get("as_of")}
        elif request.name == ResearchToolName.RECORD_EVIDENCE.value:
            result = {"entry_id": args.get("entry_id", hashlib.sha256(digest.encode()).hexdigest()[:16]), "recorded": True}
        else:
            return self._rejected(request.name, "tool is not allow-listed", request_id=request.run_id, digest=digest)
        return ResearchToolResponse(
            request_id=request.run_id,
            name=request.name,
            status=ResearchToolStatus.SUCCEEDED,
            result=result,
            provenance={"gateway": "finahinking-research-v1", "request_digest": digest, "run_id": request.run_id},
            request_digest=digest,
        )

    def _rejected(self, name: str, message: str, *, request_id: str, digest: str = "") -> ResearchToolResponse:
        return ResearchToolResponse(
            request_id=request_id,
            name=name,
            status=ResearchToolStatus.REJECTED,
            failure_kind=FailureKind.TOOL_REJECTED,
            provenance={"gateway": "finahinking-research-v1", "message_digest": stable_digest(message)},
            request_digest=digest,
        )
