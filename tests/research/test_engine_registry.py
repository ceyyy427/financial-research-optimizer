"""Governed optional quant-engine registry tests."""

from __future__ import annotations

import pytest

from finahinking.p8_2.contracts import MLResearchSpecification, ParameterSweepSpecification
from finahinking.p8_2.data_sources import FixtureMarketDataSource
from finahinking.research.engine_registry import (
    EngineRegistry,
    FinathinkSpecification,
    RegistryStatus,
)


class _NoopAdapter:
    def run(self, spec, dataset):
        raise AssertionError("unavailable adapter must never execute")


def _ml_request() -> FinathinkSpecification:
    dataset = FixtureMarketDataSource().snapshot()
    spec = MLResearchSpecification(
        research_id="registry-demo",
        dataset_fingerprint=dataset.fingerprint,
        target="close",
        features=("close",),
        train_scope={"start": "2026-01-01", "end": "2026-01-04"},
        validation_scope={"start": "2026-01-04", "end": "2026-01-06"},
        test_scope={"start": "2026-01-06", "end": "2026-01-10"},
    )
    return FinathinkSpecification(dataset=dataset, ml=spec)


def _sweep_request() -> FinathinkSpecification:
    dataset = FixtureMarketDataSource().snapshot()
    spec = ParameterSweepSpecification(parameter_ranges={"window": (5, 10)})
    return FinathinkSpecification(dataset=dataset, sweep=spec)


def test_registry_keeps_optional_engines_deferred_without_installing_or_downloading() -> None:
    registry = EngineRegistry()
    registry.register(
        "qlib",
        capability="ml",
        adapter=_NoopAdapter(),
        isolation={"installed": False},
    )

    assert registry.status("qlib") == RegistryStatus.NOT_INSTALLED
    result = registry.run("qlib", _ml_request())

    assert result.engine == "finathink-deterministic-baseline"
    assert result.fallback_used is True
    assert result.fallback_reason == "qlib is not installed in the approved isolated environment"
    assert "download" not in result.to_json().lower()


def test_registry_requires_all_admission_gates_before_available() -> None:
    registry = EngineRegistry()
    registry.register(
        "vectorbt",
        capability="sweep",
        adapter=_NoopAdapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": False,
            "fallback": True,
        },
    )

    assert registry.status("vectorbt") == RegistryStatus.DEFERRED
    details = registry.describe("vectorbt")
    assert details["missing_gates"] == ("raw_object_boundary",)
    result = registry.run("vectorbt", _sweep_request())
    assert result.status == "COMPLETE"
    assert result.fallback_used is True
    assert result.fallback_reason == "vectorbt admission gates are incomplete"


def test_registry_accepts_only_finathink_owned_normalized_data() -> None:
    registry = EngineRegistry()
    registry.register("internal", capability="ml", adapter=_NoopAdapter(), isolation={"installed": True})

    with pytest.raises(TypeError, match="FinathinkSpecification"):
        registry.run("internal", object())

    with pytest.raises(TypeError, match="DatasetSnapshot"):
        registry.run("internal", FinathinkSpecification(dataset={"close": 1}, ml=_ml_request().ml))


def test_admitted_adapter_result_is_normalized_and_reports_actual_engine() -> None:
    class FixtureAdapter:
        def run(self, spec, dataset):
            from finahinking.p8_2.ml import run_deterministic_baseline

            baseline = run_deterministic_baseline(spec, dataset)
            return baseline.__class__(
                specification_fingerprint=baseline.specification_fingerprint,
                dataset_fingerprint=baseline.dataset_fingerprint,
                status="COMPLETE",
                engine="fixture-qlib",
                metrics=baseline.metrics,
                predictions=baseline.predictions,
                feature_importance=baseline.feature_importance,
                limitations=baseline.limitations,
                fallback_used=False,
                model_artifact={"kind": "fixture"},
            )

    registry = EngineRegistry()
    registry.register(
        "qlib",
        capability="ml",
        adapter=FixtureAdapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
        },
    )

    assert registry.status("qlib") == RegistryStatus.AVAILABLE
    result = registry.run("qlib", _ml_request())
    assert result.engine == "fixture-qlib"
    assert result.fallback_used is False
    assert result.fallback_reason is None


def test_unknown_engine_is_typed_fallback_and_does_not_execute_user_code() -> None:
    registry = EngineRegistry()
    assert registry.status("unknown") == RegistryStatus.NOT_INSTALLED
    result = registry.run("unknown", _ml_request())
    assert result.fallback_used is True
    assert result.fallback_reason == "unknown is not installed in the approved isolated environment"
