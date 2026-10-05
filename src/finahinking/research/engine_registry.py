"""Governed registry for optional, isolated quantitative research engines.

The registry is intentionally provider-neutral.  It accepts only Finathink's
normalized :class:`DatasetSnapshot` and typed ML/sweep specifications.  An
optional package can accelerate an experiment only after all admission gates
are explicit; otherwise the deterministic in-house engine is used and the
reason remains part of the result.
"""

from __future__ import annotations

import builtins
import multiprocessing
import re
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from finahinking.p8_2.contracts import (
    DatasetSnapshot,
    MLResearchResult,
    MLResearchSpecification,
    ParameterSweepSpecification,
    SweepResult,
)
from finahinking.p8_2.ml import run_deterministic_baseline
from finahinking.p8_2.sweeps import run_parameter_sweep


class RegistryStatus:
    """Stable status strings suitable for API/UI payloads."""

    AVAILABLE: ClassVar[str] = "AVAILABLE"
    NOT_INSTALLED: ClassVar[str] = "NOT_INSTALLED"
    DEFERRED: ClassVar[str] = "DEFERRED"


def _restricted_worker(adapter: Any, specification: Any, dataset: DatasetSnapshot, result_queue: Any) -> None:
    """Run one adapter call in a deny-by-default worker process."""

    class _NetworkDeniedSocket:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise PermissionError("network access is disabled in the research worker")

    def _network_denied(*args: Any, **kwargs: Any) -> Any:
        raise PermissionError("network access is disabled in the research worker")

    def _write_denied_open(*args: Any, **kwargs: Any) -> Any:
        mode = kwargs.get("mode", args[1] if len(args) > 1 else "r")
        if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
            raise PermissionError("file writes are disabled in the research worker")
        return _ORIGINAL_OPEN(*args, **kwargs)

    try:
        socket.socket = _NetworkDeniedSocket  # type: ignore[assignment]
        socket.create_connection = _network_denied  # type: ignore[assignment]
        builtins.open = _write_denied_open  # type: ignore[assignment]
        result = adapter.run(specification, dataset)
        result_queue.put(("ok", result))
    except Exception as exc:  # noqa: BLE001 - worker reports only a typed error
        result_queue.put(("error", type(exc).__name__[:80] or "AdapterError"))


_ORIGINAL_OPEN = builtins.open


@dataclass(frozen=True, slots=True)
class RestrictedProcessRunner:
    """Small process boundary used for optional adapters.

    This is intentionally conservative: no network sockets or file writes are
    available in the worker, and timeout termination prevents a stuck adapter
    from blocking the research process.  It is not a general sandbox for
    arbitrary untrusted code; callers must provide this runner explicitly.
    """

    timeout_seconds: float = 30.0
    network_disabled: bool = True
    file_write_disabled: bool = True

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.timeout_seconds > 300:
            raise ValueError("runner timeout must be between 0 and 300 seconds")
        if self.network_disabled is not True or self.file_write_disabled is not True:
            raise ValueError("restricted runner must disable network and file writes")

    def run(self, adapter: Any, specification: Any, dataset: DatasetSnapshot) -> Any:
        context = multiprocessing.get_context("spawn")
        result_queue = context.Queue(maxsize=1)
        process = context.Process(target=_restricted_worker, args=(adapter, specification, dataset, result_queue))
        try:
            process.start()
        except Exception as exc:
            raise RuntimeError("adapter cannot start in the restricted worker") from exc
        process.join(self.timeout_seconds)
        if process.is_alive():
            process.terminate()
            process.join(1)
            raise TimeoutError("research adapter exceeded the worker timeout")
        try:
            state, payload = result_queue.get_nowait()
        except Exception as exc:
            raise RuntimeError("research worker returned no result") from exc
        if state == "error":
            raise RuntimeError(f"restricted adapter failed ({payload})")
        return payload


_SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|token|secret|password|prompt|raw[ _-]?provider|endpoint|url)", re.IGNORECASE)
_EXECUTABLE_KEY = re.compile(r"(?:^__|eval|exec|shell|command|script|source[_-]?code|callable|globals|builtins)", re.IGNORECASE)
_SENSITIVE_VALUE = re.compile(r"(?:api[_-]?key|token|secret|password|raw[ _-]?provider[ _-]?response|https?://|ftp://)", re.IGNORECASE)
_ABSOLUTE_PATH = re.compile(r"^(?:/|[A-Za-z]:[\\/])")


@dataclass(frozen=True, slots=True)
class FinathinkSpecification:
    """A typed request binding one research spec to one normalized dataset."""

    dataset: DatasetSnapshot
    ml: MLResearchSpecification | None = None
    sweep: ParameterSweepSpecification | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.dataset, DatasetSnapshot):
            raise TypeError("dataset must be a DatasetSnapshot")
        selected = (self.ml is not None, self.sweep is not None)
        if sum(selected) != 1:
            raise ValueError("exactly one ML or sweep specification is required")
        if self.ml is not None and not isinstance(self.ml, MLResearchSpecification):
            raise TypeError("ml must be an MLResearchSpecification")
        if self.sweep is not None and not isinstance(self.sweep, ParameterSweepSpecification):
            raise TypeError("sweep must be a ParameterSweepSpecification")
        if self.ml is not None and self.ml.dataset_fingerprint != self.dataset.fingerprint:
            raise ValueError("ML dataset fingerprint does not match normalized dataset")

    @property
    def kind(self) -> str:
        return "ml" if self.ml is not None else "sweep"

    @property
    def specification(self) -> MLResearchSpecification | ParameterSweepSpecification:
        return self.ml if self.ml is not None else self.sweep  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class EngineAdmission:
    """Evidence required before an optional adapter can be marked available."""

    installed: bool = False
    software_version: bool = False
    license: bool = False
    isolated: bool = False
    normalized_fixture: bool = False
    raw_object_boundary: bool = False
    fallback: bool = False
    controlled_runner: bool = False
    runner: RestrictedProcessRunner | None = None

    _GATES: ClassVar[tuple[str, ...]] = (
        "software_version",
        "license",
        "isolated",
        "normalized_fixture",
        "raw_object_boundary",
        "fallback",
        "controlled_runner",
    )

    def __post_init__(self) -> None:
        if self.controlled_runner != isinstance(self.runner, RestrictedProcessRunner):
            raise ValueError("controlled_runner must be derived from RestrictedProcessRunner")

    @classmethod
    def from_value(cls, value: Mapping[str, Any] | EngineAdmission | None, *, installed_default: bool) -> EngineAdmission:
        if value is None:
            return cls(installed=installed_default)
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("isolation must be a mapping or EngineAdmission")
        allowed = {"installed", *cls._GATES, "runner"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError("unknown engine admission fields")
        runner = value.get("runner")
        if runner is not None and not isinstance(runner, RestrictedProcessRunner):
            raise TypeError("runner must be a RestrictedProcessRunner")
        values: dict[str, bool] = {}
        for key in allowed:
            if key == "runner":
                continue
            raw = value.get(key, installed_default if key == "installed" else False)
            if not isinstance(raw, bool):
                raise TypeError(f"engine admission field {key} must be boolean")
            values[key] = raw
        # A caller cannot promote itself by setting a boolean.  The gate is
        # derived from the concrete deny-by-default worker instance.
        if values["controlled_runner"] and runner is None:
            values["controlled_runner"] = False
        if runner is not None:
            values["controlled_runner"] = True
        return cls(**values, runner=runner)

    @property
    def missing_gates(self) -> tuple[str, ...]:
        return tuple(key for key in self._GATES if not getattr(self, key))


@dataclass(frozen=True, slots=True)
class _Entry:
    name: str
    capability: str
    adapter: Any
    admission: EngineAdmission

    @property
    def status(self) -> str:
        if not self.admission.installed:
            return RegistryStatus.NOT_INSTALLED
        return RegistryStatus.AVAILABLE if not self.admission.missing_gates else RegistryStatus.DEFERRED


def _safe_error_type(error: Exception) -> str:
    return type(error).__name__[:80] or "AdapterError"


class EngineRegistry:
    """Register and execute optional adapters with deterministic fallbacks."""

    def __init__(self) -> None:
        self._entries: dict[str, _Entry] = {}

    def register(self, name: str, capability: str, adapter: Any, isolation: Mapping[str, Any] | EngineAdmission | None = None) -> None:
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 64:
            raise ValueError("engine name is invalid")
        normalized_name = name.strip().casefold()
        if capability not in {"ml", "sweep"}:
            raise ValueError("engine capability must be 'ml' or 'sweep'")
        if not hasattr(adapter, "run") or not callable(adapter.run):
            raise TypeError("engine adapter must expose run(specification, dataset)")
        available = getattr(adapter, "available", None)
        installed_default = bool(available()) if callable(available) else False
        admission = EngineAdmission.from_value(isolation, installed_default=installed_default)
        self._entries[normalized_name] = _Entry(normalized_name, capability, adapter, admission)

    def status(self, name: str) -> str:
        entry = self._entries.get(name.casefold() if isinstance(name, str) else "")
        return entry.status if entry is not None else RegistryStatus.NOT_INSTALLED

    def describe(self, name: str) -> dict[str, Any]:
        entry = self._entries.get(name.casefold() if isinstance(name, str) else "")
        if entry is None:
            return {"name": name, "status": RegistryStatus.NOT_INSTALLED, "missing_gates": EngineAdmission._GATES}
        return {
            "name": entry.name,
            "capability": entry.capability,
            "status": entry.status,
            "installed": entry.admission.installed,
            "missing_gates": entry.admission.missing_gates,
        }

    def run(self, name: str, request: FinathinkSpecification) -> MLResearchResult | SweepResult:
        if not isinstance(request, FinathinkSpecification):
            raise TypeError("request must be a FinathinkSpecification")
        entry = self._entries.get(name.casefold() if isinstance(name, str) else "")
        if entry is None:
            return self._fallback(request, "unknown optional engine is not installed in the approved isolated environment")
        if entry.capability != request.kind:
            raise TypeError(f"engine {entry.name} does not support {request.kind} research")
        if entry.status == RegistryStatus.AVAILABLE:
            try:
                if entry.admission.runner is None:
                    raise RuntimeError("controlled worker is not configured")
                result = entry.admission.runner.run(entry.adapter, request.specification, request.dataset)
                self._validate_result(result, request)
                return result
            except Exception as exc:  # noqa: BLE001 - adapter boundary fails closed
                fallback_reason = f"{entry.name} adapter execution failed ({_safe_error_type(exc)})"
        elif entry.status == RegistryStatus.NOT_INSTALLED:
            fallback_reason = f"{entry.name} is not installed in the approved isolated environment"
        else:
            fallback_reason = f"{entry.name} admission gates are incomplete"
        return self._fallback(request, fallback_reason)

    @staticmethod
    def _validate_result(result: Any, request: FinathinkSpecification) -> None:
        expected = MLResearchResult if request.kind == "ml" else SweepResult
        if not isinstance(result, expected):
            raise TypeError("adapter must return a Finathink-owned research result")
        expected_spec_fp = request.specification.fingerprint
        if result.specification_fingerprint != expected_spec_fp:
            raise ValueError("adapter result specification fingerprint mismatch")
        if result.dataset_fingerprint != request.dataset.fingerprint and request.kind == "ml":
            raise ValueError("adapter result dataset fingerprint mismatch")
        EngineRegistry._validate_safe_payload(result.to_dict())
        # Force contract serialization at the boundary; this also rejects raw
        # third-party objects nested in predictions or artifacts.
        result.to_json()

    @staticmethod
    def _validate_safe_payload(value: Any, *, key: str = "") -> None:
        if isinstance(value, Mapping):
            for raw_key, item in value.items():
                if not isinstance(raw_key, str):
                    raise TypeError("adapter result keys must be strings")
                if _EXECUTABLE_KEY.search(raw_key) or _SENSITIVE_KEY.search(raw_key):
                    raise ValueError("adapter result contains a restricted field")
                EngineRegistry._validate_safe_payload(item, key=raw_key)
            return
        if isinstance(value, (tuple, list)):
            for item in value:
                EngineRegistry._validate_safe_payload(item, key=key)
            return
        if isinstance(value, str):
            if _SENSITIVE_VALUE.search(value) or _ABSOLUTE_PATH.match(value.strip()):
                raise ValueError("adapter result contains a restricted value")
            return
        if value is None or isinstance(value, (bool, int, float)):
            return
        raise TypeError("adapter result contains a raw object")

    @staticmethod
    def _fallback(request: FinathinkSpecification, reason: str) -> MLResearchResult | SweepResult:
        if request.ml is not None:
            baseline = run_deterministic_baseline(request.ml, request.dataset)
            return MLResearchResult(
                specification_fingerprint=baseline.specification_fingerprint,
                dataset_fingerprint=baseline.dataset_fingerprint,
                status="FALLBACK",
                engine=baseline.engine,
                metrics=baseline.metrics,
                predictions=baseline.predictions,
                feature_importance=baseline.feature_importance,
                limitations=baseline.limitations,
                fallback_used=True,
                model_artifact=baseline.model_artifact,
                fallback_reason=reason,
            )

        assert request.sweep is not None
        closes = tuple(item.close for item in request.dataset.observations)
        average = sum(closes) / len(closes)

        def evaluate(parameters: dict[str, Any]) -> dict[str, Any]:
            window = parameters.get("window", 1)
            try:
                divisor = max(1.0, float(window))
            except (TypeError, ValueError):
                divisor = 1.0
            return {"oos": {"score": average / divisor}, "train": {}, "validation": {}}

        result = run_parameter_sweep(request.sweep, evaluate)
        return SweepResult(
            specification_fingerprint=result.specification_fingerprint,
            experiments=result.experiments,
            warnings=result.warnings,
            multiple_testing=result.multiple_testing,
            robust_regions=result.robust_regions,
            unstable_regions=result.unstable_regions,
            oos_comparison=result.oos_comparison,
            engine="finathink-deterministic-sweep",
            status=result.status,
            fallback_used=True,
            fallback_reason=reason,
        )


__all__ = [
    "EngineAdmission",
    "EngineRegistry",
    "FinathinkSpecification",
    "RegistryStatus",
    "RestrictedProcessRunner",
]
