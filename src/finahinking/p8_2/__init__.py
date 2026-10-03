"""Finathink-owned P8.2 research contracts and optional capability seams.

The package intentionally contains no imports from optional Qlib, vectorbt, or
QMT SDKs.  Providers cross into Finathink through the small typed interfaces
defined in the sibling modules.
"""

from .contracts import (
    DatasetSnapshot,
    FeatureObservation,
    MarketObservation,
    MLDatasetSplit,
    MLModelSpecification,
    MLResearchResult,
    MLResearchSpecification,
    ModelMetric,
    ParameterSweepSpecification,
    ResearchPoint,
    SweepResult,
)

__all__ = [
    "DatasetSnapshot",
    "FeatureObservation",
    "MLDatasetSplit",
    "MLModelSpecification",
    "MLResearchResult",
    "MLResearchSpecification",
    "MarketObservation",
    "ModelMetric",
    "ParameterSweepSpecification",
    "ResearchPoint",
    "SweepResult",
]
