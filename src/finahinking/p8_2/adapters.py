"""Optional research-engine adapter seams.

Qlib remains optional and isolated.  The adapter returns Finathink contracts
even when Qlib is unavailable, so core startup has no optional import path.
"""

from __future__ import annotations

import importlib.util

from .contracts import (
    DatasetSnapshot,
    MLResearchResult,
    MLResearchSpecification,
    ParameterSweepSpecification,
    SweepResult,
)
from .ml import run_deterministic_baseline
from .sweeps import run_parameter_sweep


class QlibResearchAdapter:
    """Typed Qlib seam with a deterministic Finathink fallback."""

    def __init__(self, *, force_unavailable: bool = False) -> None:
        self.force_unavailable = force_unavailable

    @staticmethod
    def available() -> bool:
        try:
            return importlib.util.find_spec("qlib") is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    def run(self, spec: MLResearchSpecification, dataset: DatasetSnapshot) -> MLResearchResult:
        if not isinstance(spec, MLResearchSpecification):
            raise TypeError("spec must be an MLResearchSpecification")
        if not isinstance(dataset, DatasetSnapshot):
            raise TypeError("dataset must be a DatasetSnapshot")
        result = run_deterministic_baseline(spec, dataset)
        if self.force_unavailable or not self.available():
            return MLResearchResult(
                specification_fingerprint=result.specification_fingerprint,
                dataset_fingerprint=result.dataset_fingerprint,
                status="NOT_INSTALLED",
                engine="finathink-deterministic-baseline",
                metrics=result.metrics,
                predictions=result.predictions,
                feature_importance=result.feature_importance,
                limitations=(
                    "Qlib is optional and unavailable in the core environment; this result is a local fallback.",
                    *result.limitations,
                ),
                fallback_used=True,
                model_artifact=result.model_artifact,
                fallback_reason="qlib is not installed in the approved isolated environment",
            )
        # Availability alone does not grant permission to leak Qlib objects;
        # the first slice still uses the transparent baseline until an isolated
        # Qlib environment passes its compatibility and provenance checks.
        return MLResearchResult(
            specification_fingerprint=result.specification_fingerprint,
            dataset_fingerprint=result.dataset_fingerprint,
            status="FALLBACK",
            engine="finathink-deterministic-baseline",
            metrics=result.metrics,
            predictions=result.predictions,
            feature_importance=result.feature_importance,
            limitations=(
                "Qlib was detected but the isolated adapter smoke gate is not yet admitted; baseline retained.",
                *result.limitations,
            ),
            fallback_used=True,
            model_artifact=result.model_artifact,
            fallback_reason="qlib admission gates are incomplete",
        )


class VectorbtSweepAdapter:
    """Optional vectorbt seam returning only Finathink ``SweepResult`` values."""

    def __init__(self, *, force_unavailable: bool = False) -> None:
        self.force_unavailable = force_unavailable

    @staticmethod
    def available() -> bool:
        try:
            return importlib.util.find_spec("vectorbt") is not None
        except (ImportError, ModuleNotFoundError, ValueError):
            return False

    def run(self, spec: ParameterSweepSpecification, dataset: DatasetSnapshot) -> SweepResult:
        if not isinstance(spec, ParameterSweepSpecification):
            raise TypeError("spec must be a ParameterSweepSpecification")
        if not isinstance(dataset, DatasetSnapshot):
            raise TypeError("dataset must be a DatasetSnapshot")
        average = sum(item.close for item in dataset.observations) / len(dataset.observations)

        def evaluate(parameters: dict[str, object]) -> dict[str, object]:
            try:
                window = max(1.0, float(parameters.get("window", 1)))
            except (TypeError, ValueError):
                window = 1.0
            return {"train": {}, "validation": {}, "oos": {"score": average / window}}

        result = run_parameter_sweep(spec, evaluate)
        # Import visibility is not an admission decision.  Until a concrete
        # restricted vectorbt runner is supplied, this adapter intentionally
        # reports the Finathink sweep as the actual engine.
        reason = "vectorbt runner is not admitted; Finathink sweep is the deterministic fallback"
        return SweepResult(
            specification_fingerprint=result.specification_fingerprint,
            experiments=result.experiments,
            warnings=result.warnings,
            multiple_testing=result.multiple_testing,
            robust_regions=result.robust_regions,
            unstable_regions=result.unstable_regions,
            oos_comparison=result.oos_comparison,
            engine="finathink-deterministic-sweep",
            status="FALLBACK",
            fallback_used=True,
            fallback_reason=reason,
        )


__all__ = ["QlibResearchAdapter", "VectorbtSweepAdapter"]
