"""Governed registry for optional, isolated quantitative research engines.

The registry is intentionally provider-neutral.  It accepts only Finathink's
normalized :class:`DatasetSnapshot` and typed ML/sweep specifications.  An
optional package can accelerate an experiment only after all admission gates
are explicit; otherwise the deterministic in-house engine is used and the
reason remains part of the result.
"""

from __future__ import annotations

import math
import re
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


@dataclass(frozen=True, slots=True)
class EngineAdmissionEvidence:
    """Bindings to deployment-owned external audit receipts.

    Digests identify the version/dependency, license and OS/container policy
    audits. They are references, not proof by themselves: a separately supplied
    verifier must validate them against the deployment's trusted audit store.
    The core ships no verifier that grants admission.
    """

    engine_name: str
    pinned_version: str
    runtime_version: str
    license_name: str
    version_audit_digest: str
    license_audit_digest: str
    sandbox_audit_digest: str
    fixture_digest: str

    def __post_init__(self) -> None:
        for name in ("engine_name", "pinned_version", "runtime_version", "license_name"):
            value = getattr(self, name)
            if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,95}", value):
                raise ValueError(f"{name} must be a safe audit identifier")
        for name in ("version_audit_digest", "license_audit_digest", "sandbox_audit_digest", "fixture_digest"):
            if not isinstance(getattr(self, name), str) or not re.fullmatch(r"[0-9a-f]{64}", getattr(self, name)):
                raise ValueError(f"{name} must be a SHA-256 digest")


class ExternalAdmissionVerifier:
    """Deployment integration for checking actual external admission receipts.

    Implementations must independently inspect their trusted external audit
    records and current OS/container runner, including pinned/runtime version,
    license/extras/hosting review, no-network policy and timeout termination.
    Boolean markers on the runner are never substituted for this verification.
    """

    def verify(self, evidence: EngineAdmissionEvidence, runner: TrustedSandboxRunner) -> bool:
        return False


class TrustedSandboxRunner:
    """Marker base for a separately audited OS sandbox runner.

    The registry deliberately does not trust arbitrary objects that merely
    expose ``run``. A deployment must provide a subclass backed by a real
    sandbox policy; tests may use an explicit subclass as a contract double.
    """

    trusted_sandbox: ClassVar[bool] = False
    network_disabled: ClassVar[bool] = True
    file_write_disabled: ClassVar[bool] = True
    timeout_seconds: ClassVar[float] = 30.0
    supports_termination: ClassVar[bool] = False

    def run(self, adapter: Any, specification: Any, dataset: DatasetSnapshot) -> Any:
        raise NotImplementedError("a deployment must provide the audited sandbox runner")

    def run_with_timeout(self, adapter: Any, specification: Any, dataset: DatasetSnapshot, timeout_seconds: float) -> Any:
        raise RuntimeError("runner does not provide externally enforced termination")


@dataclass(frozen=True, slots=True)
class RestrictedProcessRunner(TrustedSandboxRunner):
    """Small process boundary used for optional adapters.

    This class is intentionally disabled. Python-level monkeypatching cannot
    prove OS isolation, so it is never accepted by the registry or executed.
    Deployments must provide an audited external process/container runner.
    """

    trusted_sandbox: ClassVar[bool] = False
    timeout_seconds: float = 30.0
    network_disabled: bool = True
    file_write_disabled: bool = True

    def __post_init__(self) -> None:
        if not math.isfinite(float(self.timeout_seconds)) or self.timeout_seconds <= 0 or self.timeout_seconds > 300:
            raise ValueError("runner timeout must be between 0 and 300 seconds")
        if self.network_disabled is not True or self.file_write_disabled is not True:
            raise ValueError("restricted runner must disable network and file writes")

    def run(self, adapter: Any, specification: Any, dataset: DatasetSnapshot) -> Any:
        raise RuntimeError("RestrictedProcessRunner is disabled; provide an external OS sandbox runner")


_SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|token|secret|password|prompt|raw[ _-]?provider|endpoint|url|path)", re.IGNORECASE)
_EXECUTABLE_KEY = re.compile(
    r"(?:^__|callable|globals|builtins|(?:^|[_-])(?:code|eval|exec|shell|command|script|source)(?:$|[_-]))",
    re.IGNORECASE,
)
_SENSITIVE_VALUE = re.compile(
    r"(?:api[_-]?key|token|secret|password|raw[ _-]?provider[ _-]?response|"
    r"\b(?:eval|exec|__import__|subprocess|os\.system)\s*\()",
    re.IGNORECASE,
)
_URI_SCHEME = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9+.-]*:\/{0,2}(?=\S)")
_EMPTY_URI_SCHEME = re.compile(
    r"(?<![A-Za-z0-9_])(?:https?|ftp|file|ws|wss|data|mailto|custom|ssh|tcp|udp|tel|urn|blob|javascript|git):$",
    re.IGNORECASE,
)
_RELATIVE_PATH = re.compile(r"^[A-Za-z0-9_.-]+(?:[/\\][A-Za-z0-9_.-]+)+$")
_TRAILING_PATH = re.compile(r"^[A-Za-z0-9_.-]+[/\\]$")
_PATH_FIELD = re.compile(r"(?:path|file|location|code|source|command|script|endpoint|url)", re.IGNORECASE)
_CODE_FIELD = re.compile(r"(?:code|source|script|command|eval|exec)", re.IGNORECASE)
_CODE_LINE = re.compile(
    r"(?:^|[;{]|:\s*)(?:def\s+[A-Za-z_]\w*\s*\(|class\s+[A-Za-z_]\w*\s*[:(]|"
    r"import\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s*$|"
    r"from\s+[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*\s+import\s+[A-Za-z_]\w*|"
    r"return\s+[A-Za-z_]\w*(?:[.\[\]()][A-Za-z0-9_.'\"\[\]() -]*)*)",
    re.MULTILINE,
)
_CODE_HINT = re.compile(r"(?:\bpython\b|\bbash\b|\bshell\b|\bsql\b|\bjavascript\b|^#!)", re.IGNORECASE)
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
    runner: TrustedSandboxRunner | None = None
    version: str | None = None
    license_name: str | None = None
    timeout_seconds: float = 30.0
    evidence: EngineAdmissionEvidence | None = None
    verifier: ExternalAdmissionVerifier | None = None

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
        if self.controlled_runner != isinstance(self.runner, TrustedSandboxRunner) or (
            self.runner is not None and not getattr(self.runner, "trusted_sandbox", False)
        ):
            raise ValueError("controlled_runner must be derived from a trusted sandbox runner")
        if self.version is not None and (not isinstance(self.version, str) or not self.version.strip()):
            raise TypeError("engine version must be a non-empty string when provided")
        if self.license_name is not None and (not isinstance(self.license_name, str) or not self.license_name.strip()):
            raise TypeError("license name must be a non-empty string when provided")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise TypeError("engine timeout_seconds must be numeric")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 300:
            raise ValueError("engine timeout_seconds must be between 0 and 300 seconds")
        if self.evidence is not None and not isinstance(self.evidence, EngineAdmissionEvidence):
            raise TypeError("evidence must be an EngineAdmissionEvidence")
        if self.verifier is not None and not isinstance(self.verifier, ExternalAdmissionVerifier):
            raise TypeError("verifier must be an ExternalAdmissionVerifier")

    @classmethod
    def from_value(cls, value: Mapping[str, Any] | EngineAdmission | None, *, installed_default: bool) -> EngineAdmission:
        if value is None:
            return cls(installed=installed_default)
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("isolation must be a mapping or EngineAdmission")
        allowed = {"installed", *cls._GATES, "runner", "version", "engine_version", "license_name", "license_id", "timeout_seconds", "evidence", "verifier"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError("unknown engine admission fields")
        runner = value.get("runner")
        if runner is not None and (
            not isinstance(runner, TrustedSandboxRunner) or not getattr(runner, "trusted_sandbox", False)
        ):
            raise TypeError("runner must be an audited trusted sandbox runner")
        values: dict[str, bool] = {}
        metadata_keys = {"version", "engine_version", "license_name", "license_id", "timeout_seconds", "evidence", "verifier"}
        for key in allowed:
            if key == "runner" or key in metadata_keys:
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
        version = value.get("version", value.get("engine_version"))
        license_name = value.get("license_name", value.get("license_id"))
        timeout_seconds = value.get("timeout_seconds", getattr(runner, "timeout_seconds", 30.0))
        return cls(
            **values,
            runner=runner,
            version=version,
            license_name=license_name,
            timeout_seconds=timeout_seconds,
            evidence=value.get("evidence"),
            verifier=value.get("verifier"),
        )

    @property
    def missing_gates(self) -> tuple[str, ...]:
        return tuple(key for key in self._GATES if not getattr(self, key))

    def externally_verified(self, name: str) -> bool:
        evidence, verifier, runner = self.evidence, self.verifier, self.runner
        if evidence is None or verifier is None or runner is None:
            return False
        if (
            evidence.engine_name.casefold() != name
            or not self.version
            or evidence.pinned_version != self.version
            or evidence.runtime_version != self.version
            or not self.license_name
            or evidence.license_name != self.license_name
            or runner.network_disabled is not True
            or runner.file_write_disabled is not True
        ):
            return False
        try:
            return verifier.verify(evidence, runner) is True
        except Exception:  # noqa: BLE001 - external verification fails closed
            return False


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
        return RegistryStatus.AVAILABLE if (
            not self.admission.missing_gates
            and self.admission.externally_verified(self.name)
            and bool(getattr(self.admission.runner, "supports_termination", False))
            and callable(getattr(self.admission.runner, "run_with_timeout", None))
        ) else RegistryStatus.DEFERRED


@dataclass(frozen=True, slots=True)
class EngineResolution:
    """A dataset-bound, typed resolution of an optional research engine."""

    AVAILABLE: ClassVar[str] = RegistryStatus.AVAILABLE
    NOT_INSTALLED: ClassVar[str] = RegistryStatus.NOT_INSTALLED
    DEFERRED: ClassVar[str] = RegistryStatus.DEFERRED

    name: str
    status: str
    dataset: DatasetSnapshot
    capability: str | None
    engine_version: str | None
    license: str | None
    _registry: EngineRegistry

    @property
    def snapshot(self) -> DatasetSnapshot:
        """Alias used by callers that name the normalized input a snapshot."""

        return self.dataset

    def run(self, snapshot: DatasetSnapshot, spec: MLResearchSpecification | ParameterSweepSpecification) -> MLResearchResult | SweepResult:
        return self._registry._run_resolution(self, snapshot, spec)


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
            return {"name": "unknown", "status": RegistryStatus.NOT_INSTALLED, "missing_gates": EngineAdmission._GATES}
        return {
            "name": entry.name,
            "capability": entry.capability,
            "status": entry.status,
            "installed": entry.admission.installed,
            "missing_gates": entry.admission.missing_gates,
            "version": entry.admission.version,
            "license": entry.admission.license_name,
        }

    def resolve(self, name: str, dataset: DatasetSnapshot) -> EngineResolution:
        """Resolve an engine against one normalized, fingerprinted snapshot."""

        if not isinstance(dataset, DatasetSnapshot):
            raise TypeError("dataset must be a DatasetSnapshot")
        frozen_dataset = DatasetSnapshot.from_json(dataset.to_json())
        normalized_name = name.strip().casefold() if isinstance(name, str) else ""
        entry = self._entries.get(normalized_name)
        if entry is None:
            return EngineResolution(
                name=normalized_name or "unknown",
                status=RegistryStatus.NOT_INSTALLED,
                dataset=frozen_dataset,
                capability=None,
                engine_version=None,
                license=None,
                _registry=self,
            )
        return EngineResolution(
            name=entry.name,
            status=entry.status,
            dataset=frozen_dataset,
            capability=entry.capability,
            engine_version=entry.admission.version,
            license=entry.admission.license_name,
            _registry=self,
        )

    def run(self, name: str, request: FinathinkSpecification) -> MLResearchResult | SweepResult:
        if not isinstance(request, FinathinkSpecification):
            raise TypeError("request must be a FinathinkSpecification")
        return self.resolve(name, request.dataset).run(request.dataset, request.specification)

    def _run_resolution(
        self,
        resolution: EngineResolution,
        snapshot: DatasetSnapshot,
        spec: MLResearchSpecification | ParameterSweepSpecification,
    ) -> MLResearchResult | SweepResult:
        if not isinstance(snapshot, DatasetSnapshot):
            raise TypeError("snapshot must be a DatasetSnapshot")
        if snapshot.fingerprint != resolution.dataset.fingerprint:
            raise ValueError("snapshot fingerprint does not match engine resolution")
        if not isinstance(spec, (MLResearchSpecification, ParameterSweepSpecification)):
            raise TypeError("spec must be an MLResearchSpecification or ParameterSweepSpecification")
        request = FinathinkSpecification(
            dataset=snapshot,
            ml=spec if isinstance(spec, MLResearchSpecification) else None,
            sweep=spec if isinstance(spec, ParameterSweepSpecification) else None,
        )
        try:
            self._validate_safe_payload(request.specification.to_dict())
        except (TypeError, ValueError):
            return self._fallback(request, "optional engine request contains restricted values")
        entry = self._entries.get(resolution.name.casefold())
        if entry is None:
            return self._fallback(request, "unknown optional engine is not installed in the approved isolated environment")
        if entry.capability != request.kind:
            raise TypeError(f"engine {entry.name} does not support {request.kind} research")
        if entry.status == RegistryStatus.AVAILABLE:
            try:
                if entry.admission.runner is None:
                    raise RuntimeError("controlled worker is not configured")
                result = self._run_with_timeout(entry, request)
                self._validate_result(result, request)
                annotated = self._annotate_result(result, entry, request)
                self._validate_result(annotated, request, require_sweep_dataset=True)
                return annotated
            except TimeoutError:
                fallback_reason = f"{entry.name} adapter execution timeout after {entry.admission.timeout_seconds:g} seconds"
            except Exception as exc:  # noqa: BLE001 - adapter boundary fails closed
                fallback_reason = f"{entry.name} adapter execution failed ({_safe_error_type(exc)})"
        elif entry.status == RegistryStatus.NOT_INSTALLED:
            fallback_reason = f"{entry.name} is not installed in the approved isolated environment"
        else:
            fallback_reason = f"{entry.name} admission gates are incomplete"
        return self._fallback(request, fallback_reason)

    @staticmethod
    def _run_with_timeout(entry: _Entry, request: FinathinkSpecification) -> Any:
        runner = entry.admission.runner
        if runner is None:
            raise RuntimeError("controlled worker is not configured")
        if not getattr(runner, "supports_termination", False):
            raise RuntimeError("runner termination contract is not externally verified")
        return runner.run_with_timeout(
            entry.adapter,
            request.specification,
            request.dataset,
            entry.admission.timeout_seconds,
        )

    @staticmethod
    def _annotate_result(result: MLResearchResult | SweepResult, entry: _Entry, request: FinathinkSpecification) -> MLResearchResult | SweepResult:
        metadata = {
            "engine": entry.name,
            "engine_version": entry.admission.version or "unknown",
            "license": entry.admission.license_name or "unknown",
        }
        EngineRegistry._validate_safe_payload(metadata)
        if isinstance(result, MLResearchResult):
            artifact = dict(result.model_artifact or {})
            artifact.update(metadata)
            return MLResearchResult(
                specification_fingerprint=result.specification_fingerprint,
                dataset_fingerprint=result.dataset_fingerprint,
                status=result.status,
                engine=entry.name,
                metrics=result.metrics,
                predictions=result.predictions,
                feature_importance=result.feature_importance,
                limitations=result.limitations,
                fallback_used=result.fallback_used,
                model_artifact=artifact,
                fallback_reason=result.fallback_reason,
            )
        multiple_testing = dict(result.multiple_testing)
        multiple_testing.update(metadata)
        multiple_testing["dataset_fingerprint"] = request.dataset.fingerprint
        return SweepResult(
            specification_fingerprint=result.specification_fingerprint,
            experiments=result.experiments,
            warnings=result.warnings,
            multiple_testing=multiple_testing,
            robust_regions=result.robust_regions,
            unstable_regions=result.unstable_regions,
            oos_comparison=result.oos_comparison,
            engine=entry.name,
            status=result.status,
            fallback_used=result.fallback_used,
            fallback_reason=result.fallback_reason,
        )

    @staticmethod
    def _validate_result(result: Any, request: FinathinkSpecification, *, require_sweep_dataset: bool = False) -> None:
        expected = MLResearchResult if request.kind == "ml" else SweepResult
        if not isinstance(result, expected):
            raise TypeError("adapter must return a Finathink-owned research result")
        expected_spec_fp = request.specification.fingerprint
        if result.specification_fingerprint != expected_spec_fp:
            raise ValueError("adapter result specification fingerprint mismatch")
        if request.kind == "ml" and result.dataset_fingerprint != request.dataset.fingerprint:
            raise ValueError("adapter result dataset fingerprint mismatch")
        if request.kind == "sweep":
            bound_dataset = result.multiple_testing.get("dataset_fingerprint")
            if require_sweep_dataset and bound_dataset != request.dataset.fingerprint:
                raise ValueError("adapter sweep result dataset fingerprint binding is missing")
            if bound_dataset is not None and bound_dataset != request.dataset.fingerprint:
                raise ValueError("adapter sweep result dataset fingerprint mismatch")
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
            text = value.strip()
            if (
                _URI_SCHEME.search(text)
                or _EMPTY_URI_SCHEME.search(text)
                or _SENSITIVE_VALUE.search(text)
                or _ABSOLUTE_PATH.match(text)
                or _RELATIVE_PATH.fullmatch(text)
                or _TRAILING_PATH.fullmatch(text)
                or (_PATH_FIELD.search(key) and (_RELATIVE_PATH.search(text) or _TRAILING_PATH.search(text)))
                or _CODE_LINE.search(text)
                or (_CODE_FIELD.search(key) and (_CODE_HINT.search(text) or _CODE_LINE.search(text)))
            ):
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
        sweep_spec = request.sweep
        try:
            EngineRegistry._validate_safe_payload(sweep_spec.to_dict())
        except (TypeError, ValueError):
            # Preserve the caller's fingerprint for audit linkage while using
            # a fresh, empty grid so rejected parameters cannot enter output.
            sweep_spec = ParameterSweepSpecification(strategy_version="finathink-sanitized-fallback")
        closes = tuple(item.close for item in request.dataset.observations)
        average = sum(closes) / len(closes)

        def evaluate(parameters: dict[str, Any]) -> dict[str, Any]:
            window = parameters.get("window", 1)
            try:
                divisor = max(1.0, float(window))
            except (TypeError, ValueError):
                divisor = 1.0
            return {"oos": {"score": average / divisor}, "train": {}, "validation": {}}

        result = run_parameter_sweep(sweep_spec, evaluate)
        fallback = SweepResult(
            specification_fingerprint=request.sweep.fingerprint,
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
        EngineRegistry._validate_safe_payload(fallback.to_dict())
        return fallback


__all__ = [
    "EngineAdmission",
    "EngineAdmissionEvidence",
    "EngineRegistry",
    "EngineResolution",
    "ExternalAdmissionVerifier",
    "FinathinkSpecification",
    "RegistryStatus",
    "RestrictedProcessRunner",
    "TrustedSandboxRunner",
]
