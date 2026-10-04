"""Finathink-owned regression experiment service.

The optional statsmodels adapter is deliberately contained in the quant
domain.  Guided application code receives only normalized records and never
imports or handles a statsmodels object.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from finahinking.data.models import Dataset, Provenance
from finahinking.experiments.models import ResearchRun
from finahinking.factors.core import FactorDefinition

from .adapters.statsmodels_adapter import (
    OptionalDependencyError,
    RegressionResult,
    StatsmodelsAdapter,
)
from .artifacts import Artifact, QuantRun
from .runtime import _code_commit, _dependency_versions

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")


class RegressionDependencyUnavailable(RuntimeError):
    """Raised when the governed optional regression capability is absent."""


def _identity(values: Any) -> Any:
    return values


_REGRESSION_FACTOR = FactorDefinition(
    name="ordinary_least_squares",
    definition="Linear association of a target with a pre-specified feature set.",
    explanation="Coefficients summarize a fitted historical linear relationship.",
    limitations="Association is not causality; estimates are sample- and specification-sensitive.",
    compute=_identity,
)


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


@dataclass(frozen=True)
class RegressionExperimentResult:
    regression: RegressionResult
    dataset_fingerprint: str
    research_run: ResearchRun
    quant_run: QuantRun
    artifact: Artifact
    target: str
    features: tuple[str, ...]
    provenance: dict[str, Any]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        return self.regression.fingerprint

    def normalized_result(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "result_kind": "RegressionResult",
            "parameters": self.regression.parameters,
            "metrics": self.regression.metrics,
            "uncertainty": self.regression.uncertainty,
            "dataset_fingerprint": self.dataset_fingerprint,
            "research_run_id": self.research_run.run_id,
            "quant_run_id": self.quant_run.quant_run_id,
            "artifact_id": self.artifact.artifact_id,
            "artifact_fingerprint": self.artifact.fingerprint,
            "warnings": list(self.warnings),
            "limitations": list(self.limitations),
        }


def run_regression_experiment(
    frame: pd.DataFrame,
    *,
    target: str,
    features: Sequence[str],
    question: str,
    hypothesis: str,
) -> RegressionExperimentResult:
    """Fit one bounded OLS specification and create linked research records."""

    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a DataFrame")
    target = _text(target, "target")
    if isinstance(features, (str, bytes)):
        raise TypeError("features must be a sequence of column identifiers")
    features = tuple(_text(feature, "feature") for feature in features)
    if not features or any(not _IDENTIFIER.fullmatch(feature) for feature in features):
        raise ValueError("features must be allow-listed identifiers")
    if len(set(features)) != len(features) or target in features:
        raise ValueError("target and features must be distinct")
    if not _IDENTIFIER.fullmatch(target):
        raise ValueError("target must be an allow-listed identifier")
    if "date" in frame.columns:
        index = pd.to_datetime(frame["date"], errors="raise")
        modeling_frame = frame.drop(columns=["date"]).copy()
        modeling_frame.index = index
    else:
        modeling_frame = frame.copy()
        if not isinstance(modeling_frame.index, pd.DatetimeIndex):
            modeling_frame.index = pd.date_range("2020-01-01", periods=len(modeling_frame), freq="D")
    required = (target, *features)
    if target not in modeling_frame.columns or any(feature not in modeling_frame.columns for feature in features):
        raise ValueError("target/features are not present")
    observations = modeling_frame.loc[:, list(required)].apply(pd.to_numeric, errors="raise").dropna()
    if observations.empty:
        raise ValueError("regression observations are empty")
    if len(observations) <= len(features) + 1:
        raise ValueError("regression sample is too small for the requested specification")
    try:
        adapter_result = StatsmodelsAdapter().fit_ols(observations, target, features)
    except OptionalDependencyError as exc:
        raise RegressionDependencyUnavailable(str(exc)) from exc

    dataset_frame = observations.copy()
    dataset_frame["close"] = dataset_frame[target].abs() + 1.0
    dataset = Dataset(
        dataset_frame,
        Provenance(provider="regression-fixture", source_url="offline://p6-regression"),
    )
    result_fp = adapter_result.fingerprint
    quant_id = f"regression-{result_fp[:16]}"
    research_id = f"research-{quant_id}"
    timestamp = pd.Timestamp(dataset.frame.index[-1]).isoformat()
    warnings = ("SURVIVORSHIP_BIAS_NOT_MODELED", "LIQUIDITY_NOT_MODELED")
    limitations = (
        "Regression is descriptive historical evidence, not causality or investment advice.",
        "Unmodeled market realism and sample sensitivity remain material limitations.",
    )
    provenance = {
        "dataset_version": dataset_frame.to_json(date_format="iso"),
        "code_commit": _code_commit(),
        "dependency_versions": _dependency_versions(),
        "target": target,
        "features": list(features),
        "result_fingerprint": result_fp,
        "warnings": list(warnings),
    }
    artifact = Artifact.create(
        artifact_id=f"artifact-{quant_id}",
        artifact_type="regression_evidence",
        payload={
            "regression_result": {
                "parameters": adapter_result.parameters,
                "metrics": adapter_result.metrics,
                "uncertainty": adapter_result.uncertainty,
            },
            "provenance": provenance,
        },
        created_at=timestamp,
    )
    research_run = ResearchRun.create(
        run_id=research_id,
        created_at=timestamp,
        question=_text(question, "question"),
        hypothesis=_text(hypothesis, "hypothesis"),
        dataset=dataset,
        factor=_REGRESSION_FACTOR,
        method="ordinary_least_squares_regression",
        parameters={**provenance, "artifact_fingerprint": artifact.fingerprint},
        result={
            "regression_fingerprint": result_fp,
            "artifact_fingerprint": artifact.fingerprint,
            "metrics": adapter_result.metrics,
            "uncertainty": adapter_result.uncertainty,
        },
        conclusion="The normalized regression describes historical association; it does not establish causality.",
        insight="Regression coefficients and uncertainty metrics are evidence for learning.",
        limitations=list(limitations),
        engine_version="p6-regression-v1",
    )
    quant_run = QuantRun.create(
        quant_run_id=quant_id,
        research_run_id=research_id,
        dataset_version=research_run.dataset_fingerprint,
        strategy_version="ols-v1",
        engine_version="p6-regression-v1",
        parameters={"target": target, "features": list(features), "result_fingerprint": result_fp},
        result_artifact=artifact,
        timestamp=timestamp,
    )
    return RegressionExperimentResult(
        regression=adapter_result,
        dataset_fingerprint=research_run.dataset_fingerprint,
        research_run=research_run,
        quant_run=quant_run,
        artifact=artifact,
        target=target,
        features=features,
        provenance=copy.deepcopy(provenance),
        warnings=warnings,
        limitations=limitations,
    )


__all__ = ["RegressionDependencyUnavailable", "RegressionExperimentResult", "run_regression_experiment"]
