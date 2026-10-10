"""Task 8 contract tests for optional engine admission and fallback."""

from __future__ import annotations

import pytest

from finahinking.p8_2.contracts import (
    MLResearchSpecification,
    ParameterSweepSpecification,
    SweepResult,
)
from finahinking.p8_2.data_sources import FixtureMarketDataSource
from finahinking.research.engine_registry import (
    EngineAdmissionEvidence,
    EngineRegistry,
    ExternalAdmissionVerifier,
    RegistryStatus,
    TrustedSandboxRunner,
)
from finahinking.research.workflow import ResearchOrchestrator


def _request():
    dataset = FixtureMarketDataSource().snapshot()
    spec = MLResearchSpecification(
        research_id="optional-engine-contract",
        dataset_fingerprint=dataset.fingerprint,
        target="close",
        features=("close",),
        train_scope={"start": "2026-01-01", "end": "2026-01-04"},
    )
    return dataset, spec


class _Runner(TrustedSandboxRunner):
    trusted_sandbox = True
    supports_termination = True
    timeout_seconds = 0.05

    def run(self, adapter, specification, dataset):
        return adapter.run(specification, dataset)

    def run_with_timeout(self, adapter, specification, dataset, timeout_seconds):
        return self.run(adapter, specification, dataset)


class _SlowRunner(_Runner):
    def run_with_timeout(self, adapter, specification, dataset, timeout_seconds):
        raise TimeoutError("external runner terminated optional work")


class _Verifier(ExternalAdmissionVerifier):
    def verify(self, evidence, runner):
        return True


_EVIDENCE = EngineAdmissionEvidence(
    engine_name="fixture-optional",
    pinned_version="1.2.3",
    runtime_version="1.2.3",
    license_name="BSD-3-Clause",
    version_audit_digest="0" * 64,
    license_audit_digest="1" * 64,
    sandbox_audit_digest="2" * 64,
    fixture_digest="3" * 64,
)


class _Adapter:
    def run(self, spec, dataset):
        from finahinking.p8_2.ml import run_deterministic_baseline

        result = run_deterministic_baseline(spec, dataset)
        return result.__class__(
            specification_fingerprint=result.specification_fingerprint,
            dataset_fingerprint=result.dataset_fingerprint,
            status="COMPLETE",
            engine="fixture-optional",
            metrics=result.metrics,
            predictions=result.predictions,
            feature_importance=result.feature_importance,
            limitations=result.limitations,
            fallback_used=False,
            model_artifact={"kind": "fixture"},
        )


class _SweepAdapter:
    def run(self, spec, dataset):
        from finahinking.p8_2.sweeps import run_parameter_sweep

        result = run_parameter_sweep(spec, lambda parameters: {"train": {}, "validation": {}, "oos": {"score": 1.0}})
        return SweepResult(
            specification_fingerprint=result.specification_fingerprint,
            experiments=result.experiments,
            engine="fixture-sweep",
            status="COMPLETE",
            fallback_used=False,
        )


class _ConflictingAdapter(_Adapter):
    def run(self, spec, dataset):
        result = super().run(spec, dataset)
        return result.__class__(
            specification_fingerprint=result.specification_fingerprint,
            dataset_fingerprint=result.dataset_fingerprint,
            status=result.status,
            engine="other-engine",
            metrics=result.metrics,
            predictions=result.predictions,
            feature_importance=result.feature_importance,
            limitations=result.limitations,
            fallback_used=False,
            model_artifact={"engine_version": "fake", "license": "fake"},
        )


def _admitted(registry: EngineRegistry, runner: TrustedSandboxRunner) -> None:
    registry.register(
        "fixture-optional",
        capability="ml",
        adapter=_Adapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
            "runner": runner,
            "version": "1.2.3",
            "license_name": "BSD-3-Clause",
            "evidence": _EVIDENCE,
            "verifier": _Verifier(),
        },
    )


def test_resolve_returns_status_and_run_accepts_only_matching_normalized_snapshot() -> None:
    dataset, spec = _request()
    registry = EngineRegistry()
    registry.register("fixture-optional", "ml", _Adapter(), isolation={"installed": False})

    resolution = registry.resolve("fixture-optional", dataset)

    assert resolution.status == RegistryStatus.NOT_INSTALLED
    result = resolution.run(dataset, spec)
    assert result.fallback_used is True
    assert result.engine == "finathink-deterministic-baseline"
    with pytest.raises(TypeError, match="DatasetSnapshot"):
        resolution.run({"close": 1}, spec)


def test_resolve_deferred_gate_falls_back_and_records_reason() -> None:
    dataset, spec = _request()
    registry = EngineRegistry()
    registry.register("fixture-optional", "ml", _Adapter(), isolation={"installed": True})

    resolution = registry.resolve("fixture-optional", dataset)
    result = resolution.run(dataset, spec)

    assert resolution.status == RegistryStatus.DEFERRED
    assert result.fallback_used is True
    assert result.fallback_reason == "fixture-optional admission gates are incomplete"


def test_resolve_available_records_engine_version_and_license() -> None:
    dataset, spec = _request()
    registry = EngineRegistry()
    _admitted(registry, _Runner())

    resolution = registry.resolve("fixture-optional", dataset)
    result = resolution.run(dataset, spec)

    assert resolution.status == RegistryStatus.AVAILABLE
    assert result.fallback_used is False
    assert result.model_artifact["engine_version"] == "1.2.3"
    assert result.model_artifact["license"] == "BSD-3-Clause"


def test_timeout_falls_back_to_deterministic_engine() -> None:
    dataset, spec = _request()
    registry = EngineRegistry()
    _admitted(registry, _SlowRunner())

    result = registry.resolve("fixture-optional", dataset).run(dataset, spec)

    assert result.fallback_used is True
    assert result.engine == "finathink-deterministic-baseline"
    assert "timeout" in (result.fallback_reason or "").lower()


def test_restricted_specification_values_fall_back_before_adapter_execution() -> None:
    dataset, spec = _request()
    unsafe_spec = MLResearchSpecification(
        research_id=spec.research_id,
        dataset_fingerprint=dataset.fingerprint,
        target=spec.target,
        features=spec.features,
        train_scope=spec.train_scope,
        model={"hyperparameters": {"source": "https://untrusted.example/model"}},
    )
    registry = EngineRegistry()
    _admitted(registry, _Runner())

    result = registry.resolve("fixture-optional", dataset).run(dataset, unsafe_spec)

    assert result.fallback_used is True
    assert result.engine == "finathink-deterministic-baseline"
    assert "restricted" in (result.fallback_reason or "").lower()


def test_workflow_optional_engine_seam_is_explicit_and_keeps_default_fallback() -> None:
    dataset, spec = _request()

    result = ResearchOrchestrator().run_optional_engine("missing", dataset, spec)

    assert result.engine == "finathink-deterministic-baseline"
    assert result.fallback_used is True


def test_marker_runner_and_all_boolean_gates_cannot_prove_external_admission() -> None:
    dataset, spec = _request()
    registry = EngineRegistry()
    registry.register(
        "fixture-optional",
        capability="ml",
        adapter=_Adapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
            "runner": _Runner(),
            "version": "1.2.3",
            "license_name": "BSD-3-Clause",
        },
    )

    resolution = registry.resolve("fixture-optional", dataset)

    assert resolution.status == RegistryStatus.DEFERRED
    assert resolution.run(dataset, spec).fallback_used is True


def test_timeout_runner_acknowledges_termination_before_fallback() -> None:
    dataset, spec = _request()
    registry = EngineRegistry()
    _admitted(registry, _SlowRunner())

    result = registry.resolve("fixture-optional", dataset).run(dataset, spec)

    assert result.fallback_used is True
    assert "timeout" in (result.fallback_reason or "").lower()


def test_admitted_sweep_result_is_bound_to_normalized_dataset() -> None:
    dataset, _ = _request()
    spec = ParameterSweepSpecification(parameter_ranges={"window": (1, 2)})
    registry = EngineRegistry()
    registry.register(
        "fixture-sweep",
        capability="sweep",
        adapter=_SweepAdapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
            "runner": _Runner(),
            "version": "1.2.3",
            "license_name": "BSD-3-Clause",
            "evidence": EngineAdmissionEvidence(
                engine_name="fixture-sweep",
                pinned_version="1.2.3",
                runtime_version="1.2.3",
                license_name="BSD-3-Clause",
                version_audit_digest="0" * 64,
                license_audit_digest="1" * 64,
                sandbox_audit_digest="2" * 64,
                fixture_digest="3" * 64,
            ),
            "verifier": _Verifier(),
        },
    )

    result = registry.resolve("fixture-sweep", dataset).run(dataset, spec)

    assert result.engine == "fixture-sweep"
    assert result.fallback_used is False
    assert result.multiple_testing["dataset_fingerprint"] == dataset.fingerprint


def test_restricted_sweep_parameters_are_not_echoed_by_fallback() -> None:
    dataset, _ = _request()
    spec = ParameterSweepSpecification(parameters={"url": "https://untrusted.example/private"})

    result = EngineRegistry().resolve("missing", dataset).run(dataset, spec)

    assert result.fallback_used is True
    assert "untrusted.example" not in result.to_json()


def test_admission_metadata_overrides_adapter_provenance_conflicts() -> None:
    dataset, spec = _request()
    registry = EngineRegistry()
    registry.register(
        "fixture-optional",
        capability="ml",
        adapter=_ConflictingAdapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
            "runner": _Runner(),
            "version": "1.2.3",
            "license_name": "BSD-3-Clause",
            "evidence": _EVIDENCE,
            "verifier": _Verifier(),
        },
    )

    result = registry.resolve("fixture-optional", dataset).run(dataset, spec)

    assert result.engine == "fixture-optional"
    assert result.model_artifact["engine_version"] == "1.2.3"
    assert result.model_artifact["license"] == "BSD-3-Clause"


def test_engine_version_and_runtime_version_are_verified_separately() -> None:
    dataset, spec = _request()
    registry = EngineRegistry()
    registry.register(
        "fixture-runtime",
        capability="ml",
        adapter=_Adapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
            "runner": _Runner(),
            "version": "1.2.3",
            "runtime_version": "python-3.13",
            "license_name": "BSD-3-Clause",
            "evidence": EngineAdmissionEvidence(
                engine_name="fixture-runtime",
                pinned_version="1.2.3",
                runtime_version="python-3.13",
                license_name="BSD-3-Clause",
                version_audit_digest="0" * 64,
                license_audit_digest="1" * 64,
                sandbox_audit_digest="2" * 64,
                fixture_digest="3" * 64,
            ),
            "verifier": _Verifier(),
        },
    )

    resolution = registry.resolve("fixture-runtime", dataset)

    assert resolution.status == RegistryStatus.AVAILABLE
    assert resolution.run(dataset, spec).fallback_used is False


@pytest.mark.parametrize("timeout", (float("nan"), float("inf"), 0.0, -1.0))
def test_admission_rejects_non_finite_or_non_positive_timeout(timeout: float) -> None:
    with pytest.raises((TypeError, ValueError), match="timeout"):
        from finahinking.research.engine_registry import EngineAdmission

        EngineAdmission(timeout_seconds=timeout)
