"""Parameter-sweep and optional Qlib adapter boundary tests."""

from __future__ import annotations

from finahinking.p8_2.adapters import QlibResearchAdapter
from finahinking.p8_2.contracts import MLResearchSpecification, ParameterSweepSpecification
from finahinking.p8_2.data_sources import FixtureMarketDataSource
from finahinking.p8_2.sweeps import run_parameter_sweep


def test_parameter_sweep_is_deterministic_and_reports_oos_and_multiple_testing() -> None:
    spec = ParameterSweepSpecification(
        strategy_version="demo-v1",
        parameter_ranges={"window": (5, 10), "threshold": (0.1, 0.2)},
        train_scope={"start": "2020-01-01", "end": "2022-01-01"},
        validation_scope={"start": "2022-01-01", "end": "2023-01-01"},
        oos_scope={"start": "2023-01-01", "end": "2024-01-01"},
    )

    def evaluate(parameters: dict[str, object]) -> dict[str, object]:
        score = float(parameters["window"]) / 100.0
        return {"train": {"score": score}, "oos": {"score": score - 0.01}}

    result = run_parameter_sweep(spec, evaluate)
    assert len(result.experiments) == 4
    assert result.to_dict()["experiment_count"] == 4
    assert all("oos" in item for item in result.experiments)
    assert result.multiple_testing["experiment_count"] == 4
    assert any("multiple-testing" in warning.lower() for warning in result.warnings)
    assert "best strategy" not in result.to_json().lower()
    assert result.fingerprint == run_parameter_sweep(spec, evaluate).fingerprint


def test_parameter_sweep_retains_failed_cells_instead_of_aborting() -> None:
    spec = ParameterSweepSpecification(parameter_ranges={"window": (5, 10)})

    def evaluate(parameters: dict[str, object]) -> dict[str, object]:
        if parameters["window"] == 10:
            raise RuntimeError("fixture evaluator unavailable")
        return {"status": "COMPLETE", "oos": {"score": 0.1}}

    result = run_parameter_sweep(spec, evaluate)
    assert result.status == "PARTIAL"
    assert len(result.experiments) == 2
    failed = result.experiments[1]
    assert failed["status"] == "FAILED"
    assert failed["parameters"] == {"window": 10}
    assert failed["train"] == {} and failed["validation"] == {} and failed["oos"] == {}


def test_qlib_adapter_absence_is_a_typed_fallback_and_never_leaks_external_objects() -> None:
    dataset = FixtureMarketDataSource().snapshot()
    spec = MLResearchSpecification(
        research_id="ml-demo",
        dataset_fingerprint=dataset.fingerprint,
        target="close",
        features=("close",),
        train_scope={"start": "2026-01-01", "end": "2026-01-04"},
        validation_scope={"start": "2026-01-04", "end": "2026-01-06"},
        test_scope={"start": "2026-01-06", "end": "2026-01-10"},
    )
    adapter = QlibResearchAdapter(force_unavailable=True)
    result = adapter.run(spec, dataset)
    assert result.status == "NOT INSTALLED"
    assert result.fallback_used is True
    assert result.to_dict()["dataset_fingerprint"] == dataset.fingerprint
    assert all("qlib" not in type(value).__module__.lower() for value in result.to_dict().values())
