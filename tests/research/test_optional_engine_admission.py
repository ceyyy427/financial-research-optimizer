"""Task 8 contract tests for optional engine admission and fallback."""

from __future__ import annotations

import time

import pytest

from finahinking.p8_2.contracts import MLResearchSpecification
from finahinking.p8_2.data_sources import FixtureMarketDataSource
from finahinking.research.engine_registry import (
    EngineRegistry,
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
    timeout_seconds = 0.05

    def run(self, adapter, specification, dataset):
        return adapter.run(specification, dataset)


class _SlowRunner(_Runner):
    def run(self, adapter, specification, dataset):
        time.sleep(0.2)
        return adapter.run(specification, dataset)


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
