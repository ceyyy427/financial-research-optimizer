"""P5 orchestration that links a quant result back to the frozen ResearchRun."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path
from typing import Any

import pandas as pd

from finahinking.data.models import Dataset
from finahinking.data.validation import validate_price_dataset
from finahinking.experiments.models import ResearchRun
from finahinking.factors.core import FactorDefinition, momentum_factor

from .artifacts import Artifact, QuantRun
from .engines import BacktestEngine
from .evaluation import evaluate_backtest
from .interfaces import BacktestConfig, BacktestResult, EvaluationReport, Strategy
from .portfolio import validate_target_weights


def _default_factor() -> FactorDefinition:
    return momentum_factor(2)


def _code_commit() -> str:
    """Resolve the source commit without contacting a remote repository."""

    override = os.environ.get("FINAHINKING_CODE_COMMIT", "").strip()
    if override:
        return override[:128]
    repository = Path(__file__).resolve().parents[3]
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    commit = completed.stdout.strip()
    return commit[:128] if commit else "unknown"


def _dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for distribution in ("finahinking", "numpy", "pandas", "statsmodels"):
        try:
            versions[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            versions[distribution] = "not-installed"
    return versions


@dataclass(frozen=True)
class FactorThresholdStrategy:
    """Turn a documented factor into a bounded long-only target weight."""

    factor: FactorDefinition = field(default_factory=_default_factor)
    threshold: float = 0.0
    target_weight: float = 0.75
    strategy_id: str = "momentum-threshold"
    version: str = "v1"

    def __post_init__(self) -> None:
        validate_target_weights({"asset": self.target_weight}, max_weight=1.0, long_only=True)

    def generate(self, dataset: Dataset) -> pd.Series:
        frame = validate_price_dataset(dataset.frame, "close")
        factor_values = self.factor.compute(frame["close"])
        weights = factor_values.gt(self.threshold).astype(float) * self.target_weight
        return weights.reindex(frame.index)


def run_quant_experiment(
    dataset: Dataset,
    config: BacktestConfig,
    *,
    question: str,
    hypothesis: str,
    conclusion: str,
    insight: str,
    strategy: Strategy | None = None,
    run_id: str | None = None,
) -> tuple[QuantRun, ResearchRun, EvaluationReport, BacktestResult]:
    selected_strategy = strategy or FactorThresholdStrategy()
    factor = getattr(selected_strategy, "factor", None)
    if not isinstance(factor, FactorDefinition):
        raise TypeError("strategy must expose factor metadata for provenance")
    backtest = BacktestEngine().run(dataset, selected_strategy, config)
    report = evaluate_backtest(backtest)
    identifier = run_id or f"quant-{backtest.dataset_fingerprint[:16]}"
    timestamp = pd.Timestamp(dataset.frame.index[-1]).isoformat()
    code_commit = _code_commit()
    dependency_versions = _dependency_versions()
    experiment_parameters: dict[str, Any] = {
        "strategy_id": selected_strategy.strategy_id,
        "strategy_version": selected_strategy.version,
        "config": config.to_dict(),
    }
    artifact = Artifact.create(
        artifact_id=f"artifact-{identifier}",
        artifact_type="quant_evaluation",
        payload={
            "backtest_result": backtest.to_dict(),
            "evaluation_report": report.to_dict(),
            "provenance": {
                "dataset_version": backtest.dataset_fingerprint,
                "code_commit": code_commit,
                "dependency_versions": dependency_versions,
                "parameters": experiment_parameters,
                "strategy_version": selected_strategy.version,
                "engine_version": backtest.engine_version,
                "cost_model": {"fee_bps": config.fee_bps, "slippage_bps": config.slippage_bps},
                "slippage": config.slippage_bps,
                "benchmark": config.benchmark,
                "timestamp": timestamp,
                "timestamp_kind": "dataset_as_of",
                "result_fingerprint": backtest.fingerprint,
                "evaluation_fingerprint": report.fingerprint,
            },
        },
        created_at=timestamp,
    )
    research_run = ResearchRun.create(
        run_id=f"research-{identifier}",
        created_at=timestamp,
        question=question,
        hypothesis=hypothesis,
        dataset=dataset,
        factor=factor,
        method="historical_backtest_evaluation",
        parameters={
            **experiment_parameters,
            "code_commit": code_commit,
            "dependency_versions": dependency_versions,
            "engine_version": backtest.engine_version,
            "artifact_fingerprint": artifact.fingerprint,
            "result_fingerprint": backtest.fingerprint,
            "evaluation_fingerprint": report.fingerprint,
        },
        result={
            "backtest_fingerprint": backtest.fingerprint,
            "evaluation_fingerprint": report.fingerprint,
            "artifact_fingerprint": artifact.fingerprint,
            "metrics": report.metrics,
        },
        conclusion=conclusion,
        insight=insight,
        limitations=list(report.limitations),
        engine_version=backtest.engine_version,
    )
    quant_run = QuantRun.create(
        quant_run_id=identifier,
        research_run_id=research_run.run_id,
        dataset_version=backtest.dataset_fingerprint,
        strategy_version=selected_strategy.version,
        engine_version=backtest.engine_version,
        parameters={
            **experiment_parameters,
            "code_commit": code_commit,
            "dependency_versions": dependency_versions,
            "result_fingerprint": backtest.fingerprint,
            "evaluation_fingerprint": report.fingerprint,
        },
        result_artifact=artifact,
        timestamp=timestamp,
    )
    return quant_run, research_run, report, backtest
