"""Library-neutral, agent-safe quant service contracts for P5.5.

The gateway accepts only bounded JSON data and registered service names.  It is
intentionally boring: callers cannot provide Python callables, source code, or
third-party model objects.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from finahinking.experiments.models import canonical_json

ALLOWED_TOOLS: tuple[str, ...] = (
    "quant.run_backtest",
    "quant.run_regression",
    "quant.evaluate_performance",
    "quant.analyze_risk",
    "quant.compare_benchmark",
    "quant.inspect_run",
)

DEFERRED_TOOLS: tuple[str, ...] = ("quant.optimize_portfolio",)
_FORBIDDEN_TERMS = (
    "__import__",
    "source_code",
    "generated_python",
    "generated_shell",
    "eval(",
    "exec(",
    "subprocess",
    "shell_command",
    "pip install",
    "package_install",
    "delete_artifact",
    "rewrite_provenance",
)
_FORBIDDEN_KEYS = {
    "__class__",
    "__code__",
    "__globals__",
    "__import__",
    "callable",
    "command",
    "delete",
    "delete_artifact",
    "eval",
    "exec",
    "generated_python",
    "generated_shell",
    "import",
    "imports",
    "module",
    "package_install",
    "path",
    "file_path",
    "source",
    "source_code",
    "shell_command",
    "subprocess",
    "rewrite_provenance",
}
_FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"(?:__import__|eval\s*\(|exec\s*\()", re.IGNORECASE),
    re.compile(r"\b(?:subprocess|os\.system|popen|shell_command)\b", re.IGNORECASE),
    re.compile(r"\b(?:pip|conda|uv)\s+install\b", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?:python|python3|bash|sh|zsh)\s+-c\b", re.IGNORECASE),
)
_ARBITRARY_LOCATION = re.compile(r"(?:^[~/]|^\.\.?/|^[A-Za-z]:[\\/]|^[A-Za-z][A-Za-z0-9+.-]*://)")


class ToolStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class ToolFailureCode(str, Enum):
    UNKNOWN_TOOL = "UNKNOWN_TOOL"
    UNSAFE_REQUEST = "UNSAFE_REQUEST"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    ADAPTER_UNAVAILABLE = "ADAPTER_UNAVAILABLE"


def _contains_forbidden_text(value: Any, *, reject_locations: bool = True) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).casefold().replace("-", "_")
            if normalized_key in _FORBIDDEN_KEYS:
                return True
            if _contains_forbidden_text(key, reject_locations=reject_locations) or _contains_forbidden_text(item, reject_locations=reject_locations):
                return True
        return False
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_text(item, reject_locations=reject_locations) for item in value)
    if isinstance(value, str):
        lowered = value.casefold()
        if any(term in lowered for term in _FORBIDDEN_TERMS):
            return True
        if reject_locations and _ARBITRARY_LOCATION.search(value):
            return True
        return any(pattern.search(value) for pattern in _FORBIDDEN_VALUE_PATTERNS)
    return False


def _safe_json(value: Any, *, label: str = "payload", reject_locations: bool = True) -> Any:
    if callable(value):
        raise TypeError(f"{label} cannot contain callables")
    if _contains_forbidden_text(value, reject_locations=reject_locations):
        raise ValueError(f"{label} contains a forbidden execution directive")
    try:
        encoded = canonical_json(value)
        normalized = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{label} must be bounded JSON data") from exc
    return normalized


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    parameters: dict[str, Any]
    request_id: str = field(default_factory=lambda: f"request-{uuid.uuid4().hex}")
    research_run_id: str | None = None

    def __post_init__(self) -> None:
        # Unknown names are allowed as an envelope so the gateway can return a
        # structured rejection rather than raising at the edge.
        if not isinstance(self.tool_name, str) or not self.tool_name.strip():
            raise ValueError("tool_name is required")
        if not isinstance(self.parameters, dict):
            raise TypeError("parameters must be a mapping")
        object.__setattr__(self, "parameters", _safe_json(self.parameters, label="parameters"))
        if not isinstance(self.request_id, str) or not self.request_id.strip() or "/" in self.request_id:
            raise ValueError("request_id is invalid")
        if self.research_run_id is not None and (not isinstance(self.research_run_id, str) or not self.research_run_id.strip()):
            raise ValueError("research_run_id is invalid")

    @property
    def fingerprint(self) -> str:
        return _fingerprint({"tool_name": self.tool_name, "parameters": self.parameters, "research_run_id": self.research_run_id})

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "tool_name": self.tool_name,
            "parameters": copy.deepcopy(self.parameters),
            "request_id": self.request_id,
            "research_run_id": self.research_run_id,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class ToolResponse:
    request_id: str
    tool_name: str
    status: ToolStatus
    result: Any = None
    research_run_id: str | None = None
    quant_run_id: str | None = None
    artifact_fingerprint: str | None = None
    result_fingerprint: str | None = None
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    failure_code: ToolFailureCode | None = None
    message: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, ToolStatus):
            object.__setattr__(self, "status", ToolStatus(self.status))
        object.__setattr__(self, "provenance", _safe_json(dict(self.provenance), label="provenance", reject_locations=False))
        object.__setattr__(self, "warnings", tuple(str(value) for value in self.warnings))
        object.__setattr__(self, "limitations", tuple(str(value) for value in self.limitations))
        if self.status in {ToolStatus.REJECTED, ToolStatus.FAILED, ToolStatus.UNAVAILABLE} and self.failure_code is None:
            raise ValueError("failed responses require failure_code")
        if self.failure_code is not None and not isinstance(self.failure_code, ToolFailureCode):
            object.__setattr__(self, "failure_code", ToolFailureCode(self.failure_code))
        if self.result is not None:
            # Store only serializable normalized evidence.  Foreign objects and
            # executable-looking values are rejected before they reach callers.
            _safe_json(self.result, label="result", reject_locations=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "request_id": self.request_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "result": copy.deepcopy(self.result),
            "research_run_id": self.research_run_id,
            "quant_run_id": self.quant_run_id,
            "artifact_fingerprint": self.artifact_fingerprint,
            "result_fingerprint": self.result_fingerprint,
            "provenance": copy.deepcopy(self.provenance),
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
            "failure_code": self.failure_code.value if self.failure_code else None,
            "message": self.message,
        }


class _TypedRequest(ToolRequest):
    tool_constant = ""

    def __init__(self, parameters: dict[str, Any], *, request_id: str | None = None, research_run_id: str | None = None) -> None:
        super().__init__(self.tool_constant, parameters, request_id or f"request-{uuid.uuid4().hex}", research_run_id)


class RunBacktestRequest(_TypedRequest):
    tool_constant = "quant.run_backtest"


class RunRegressionRequest(_TypedRequest):
    tool_constant = "quant.run_regression"


class EvaluatePerformanceRequest(_TypedRequest):
    tool_constant = "quant.evaluate_performance"


class AnalyzeRiskRequest(_TypedRequest):
    tool_constant = "quant.analyze_risk"


class CompareBenchmarkRequest(_TypedRequest):
    tool_constant = "quant.compare_benchmark"


class InspectRunRequest(_TypedRequest):
    tool_constant = "quant.inspect_run"


Handler = Callable[[dict[str, Any]], Any]


class QuantServiceGateway:
    """Allow-listed dispatcher used by P6 and future MCP wrappers."""

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}
        self._records: dict[str, Any] = {}

    def register(self, tool_name: str, handler: Handler) -> None:
        if tool_name not in ALLOWED_TOOLS:
            raise ValueError("tool is not allow-listed")
        if not callable(handler):
            raise TypeError("handler must be callable")
        self._handlers[tool_name] = handler

    def register_record(self, run_id: str, record: Any) -> None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id is required")
        _safe_json(record.to_dict() if hasattr(record, "to_dict") else record, label="record", reject_locations=False)
        self._records[run_id] = record

    @property
    def approved_tools(self) -> tuple[str, ...]:
        return ALLOWED_TOOLS

    def authorize(self, tool_name: str) -> bool:
        """Return whether a name can cross the domain boundary."""

        return tool_name in ALLOWED_TOOLS

    def run_backtest(self, request: RunBacktestRequest | ToolRequest) -> ToolResponse:
        return self.execute(request)

    def run_regression(self, request: RunRegressionRequest | ToolRequest) -> ToolResponse:
        return self.execute(request)

    def evaluate_performance(self, request: EvaluatePerformanceRequest | ToolRequest) -> ToolResponse:
        return self.execute(request)

    def analyze_risk(self, request: AnalyzeRiskRequest | ToolRequest) -> ToolResponse:
        return self.execute(request)

    def compare_benchmark(self, request: CompareBenchmarkRequest | ToolRequest) -> ToolResponse:
        return self.execute(request)

    def inspect_run(self, request: InspectRunRequest | ToolRequest) -> ToolResponse:
        return self.execute(request)

    def execute_tool(self, request: ToolRequest) -> ToolResponse:
        return self.execute(request)

    def execute(self, request: ToolRequest) -> ToolResponse:
        if not isinstance(request, ToolRequest):
            return ToolResponse(
                request_id="unknown",
                tool_name="unknown",
                status=ToolStatus.REJECTED,
                failure_code=ToolFailureCode.INVALID_REQUEST,
                message="request must be a ToolRequest",
            )
        if request.tool_name not in ALLOWED_TOOLS:
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.REJECTED,
                failure_code=ToolFailureCode.UNKNOWN_TOOL,
                message="tool is not allow-listed",
            )
        if request.tool_name == "quant.inspect_run" and request.tool_name not in self._handlers:
            run_id = str(request.parameters.get("run_id", ""))
            record = self._records.get(run_id)
            if record is None:
                return ToolResponse(
                    request_id=request.request_id,
                    tool_name=request.tool_name,
                    status=ToolStatus.FAILED,
                    failure_code=ToolFailureCode.EXECUTION_ERROR,
                    message="run was not found",
                )
            result = record.to_dict() if hasattr(record, "to_dict") else record
            projection = request.parameters.get("projection")
            allowed_projections = {"summary", "provenance", "warnings", "limitations", "metrics", "full"}
            if projection is not None and projection not in allowed_projections:
                return ToolResponse(
                    request_id=request.request_id,
                    tool_name=request.tool_name,
                    status=ToolStatus.REJECTED,
                    failure_code=ToolFailureCode.INVALID_REQUEST,
                    message="inspection projection is not allow-listed",
                )
            if projection and projection != "full" and isinstance(result, dict):
                if projection == "summary":
                    result = {key: result[key] for key in ("schema_version", "id", "run_id", "research_run_id", "fingerprint") if key in result}
                else:
                    result = {projection: result.get(projection)}
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.SUCCEEDED,
                result=result,
                result_fingerprint=getattr(record, "fingerprint", None),
                provenance={"gateway": "finahinking-typed-v1", "request_fingerprint": request.fingerprint},
            )
        handler = self._handlers.get(request.tool_name)
        if handler is None:
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILED,
                failure_code=ToolFailureCode.NOT_IMPLEMENTED,
                message="tool has no registered domain service",
            )
        try:
            raw = handler(copy.deepcopy(request.parameters))
            if isinstance(raw, ToolResponse):
                return raw
            if hasattr(raw, "to_dict"):
                result = raw.to_dict()
                result_fingerprint = getattr(raw, "fingerprint", None)
            else:
                result = _safe_json(raw, label="handler result", reject_locations=False)
                result_fingerprint = _fingerprint(result)
            research_run_id = result.get("research_run_id") if isinstance(result, dict) else request.research_run_id
            quant_run_id = result.get("quant_run_id") if isinstance(result, dict) else None
            artifact_fingerprint = result.get("artifact_fingerprint") if isinstance(result, dict) else None
            warnings = tuple(result.get("warnings", ())) if isinstance(result, dict) else ()
            limitations = tuple(result.get("limitations", ())) if isinstance(result, dict) else ()
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.SUCCEEDED,
                result=result,
                research_run_id=research_run_id,
                quant_run_id=quant_run_id,
                artifact_fingerprint=artifact_fingerprint,
                result_fingerprint=result_fingerprint,
                provenance={"gateway": "finahinking-typed-v1", "request_fingerprint": request.fingerprint},
                warnings=warnings,
                limitations=limitations,
            )
        except (TypeError, ValueError) as exc:
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.REJECTED,
                failure_code=ToolFailureCode.INVALID_REQUEST,
                message=str(exc),
            )
        except (ArithmeticError, AttributeError, KeyError, RuntimeError) as exc:
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILED,
                failure_code=ToolFailureCode.EXECUTION_ERROR,
                message=f"domain service failed: {type(exc).__name__}",
            )
        except Exception:  # noqa: BLE001 - gateway must sanitize every domain failure
            # Never leak arbitrary exception text or foreign traceback data
            # through the agent-facing boundary.
            return ToolResponse(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolStatus.FAILED,
                failure_code=ToolFailureCode.EXECUTION_ERROR,
                message="domain service failed",
            )


__all__ = [
    "ALLOWED_TOOLS",
    "DEFERRED_TOOLS",
    "AnalyzeRiskRequest",
    "CompareBenchmarkRequest",
    "EvaluatePerformanceRequest",
    "InspectRunRequest",
    "QuantServiceGateway",
    "RunBacktestRequest",
    "RunRegressionRequest",
    "ToolFailureCode",
    "ToolRequest",
    "ToolResponse",
    "ToolStatus",
]
