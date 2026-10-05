"""Governed optional quant-engine registry tests."""

from __future__ import annotations

import pytest

from finahinking.p8_2.contracts import MLResearchSpecification, ParameterSweepSpecification
from finahinking.p8_2.data_sources import FixtureMarketDataSource
from finahinking.research.engine_registry import (
    EngineRegistry,
    FinathinkSpecification,
    RegistryStatus,
    RestrictedProcessRunner,
    TrustedSandboxRunner,
)


class _NoopAdapter:
    def run(self, spec, dataset):
        raise AssertionError("unavailable adapter must never execute")


class _AdmittedAdapter:
    def run(self, spec, dataset):
        from finahinking.p8_2.ml import run_deterministic_baseline

        result = run_deterministic_baseline(spec, dataset)
        return result.__class__(
            specification_fingerprint=result.specification_fingerprint,
            dataset_fingerprint=result.dataset_fingerprint,
            status="COMPLETE",
            engine="fixture-qlib",
            metrics=result.metrics,
            predictions=result.predictions,
            feature_importance=result.feature_importance,
            limitations=result.limitations,
            fallback_used=False,
            model_artifact={"kind": "fixture"},
        )


class _FakeTrustedRunner(TrustedSandboxRunner):
    def run(self, adapter, specification, dataset):
        return adapter.run(specification, dataset)


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
            "controlled_runner": True,
        },
    )

    assert registry.status("vectorbt") == RegistryStatus.DEFERRED
    details = registry.describe("vectorbt")
    assert details["missing_gates"] == ("raw_object_boundary", "controlled_runner")
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
    registry = EngineRegistry()
    registry.register(
        "qlib",
        capability="ml",
        adapter=_AdmittedAdapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
            "controlled_runner": True,
            "runner": _FakeTrustedRunner(),
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
    assert result.fallback_reason == "unknown optional engine is not installed in the approved isolated environment"
    assert registry.describe("api_key=/tmp/key")["name"] == "unknown"


def test_isolation_boolean_without_controlled_runner_can_never_be_available() -> None:
    registry = EngineRegistry()
    registry.register(
        "qlib",
        capability="ml",
        adapter=_NoopAdapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
            "controlled_runner": True,
        },
    )
    assert registry.status("qlib") == RegistryStatus.DEFERRED
    assert "controlled_runner" in registry.describe("qlib")["missing_gates"]


def test_monkeypatch_only_runner_is_rejected_as_untrusted() -> None:
    registry = EngineRegistry()
    with pytest.raises(TypeError, match="trusted sandbox"):
        registry.register(
            "qlib",
            capability="ml",
            adapter=_NoopAdapter(),
            isolation={"installed": True, "runner": RestrictedProcessRunner()},
        )


def test_sensitive_adapter_payload_is_rejected_and_falls_back() -> None:
    class SensitiveAdapter:
        def run(self, spec, dataset):
            result = _AdmittedAdapter().run(spec, dataset)
            return result.__class__(
                specification_fingerprint=result.specification_fingerprint,
                dataset_fingerprint=result.dataset_fingerprint,
                status="COMPLETE",
                engine="fixture-qlib",
                metrics=result.metrics,
                predictions=({"api_key": "top-secret"},),
                feature_importance=result.feature_importance,
                limitations=result.limitations,
                fallback_used=False,
            )

    registry = EngineRegistry()
    registry.register(
        "qlib",
        capability="ml",
        adapter=SensitiveAdapter(),
        isolation={
            "installed": True,
            "software_version": True,
            "license": True,
            "isolated": True,
            "normalized_fixture": True,
            "raw_object_boundary": True,
            "fallback": True,
            "runner": _FakeTrustedRunner(),
        },
    )
    result = registry.run("qlib", _ml_request())
    assert result.fallback_used is True
    assert result.fallback_reason == "qlib adapter execution failed (ValueError)"
    assert "top-secret" not in result.to_json()


def test_vectorbt_fallback_has_actual_finathink_engine() -> None:
    from finahinking.p8_2.adapters import VectorbtSweepAdapter

    result = VectorbtSweepAdapter(force_unavailable=False).run(_sweep_request().sweep, _sweep_request().dataset)
    assert result.engine == "finathink-deterministic-sweep"
    assert result.status == "FALLBACK"
    assert result.fallback_used is True
