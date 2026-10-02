"""P5 orchestration that links a quant result back to the frozen ResearchRun."""

from __future__ import annotations

from dataclasses import dataclass, field

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
    if not isinstance(selected_strategy, FactorThresholdStrategy):
        factor = getattr(selected_strategy, "factor", momentum_factor(2))
    else:
        factor = selected_strategy.factor
    backtest = BacktestEngine().run(dataset, selected_strategy, config)
    report = evaluate_backtest(backtest)
    identifier = run_id or f"quant-{backtest.dataset_fingerprint[:16]}"
    timestamp = pd.Timestamp(dataset.frame.index[-1]).isoformat()
    artifact = Artifact.create(
        artifact_id=f"artifact-{identifier}",
        artifact_type="quant_evaluation",
        payload={
            "backtest_result": backtest.to_dict(),
            "evaluation_report": report.to_dict(),
            "provenance": {
                "dataset_version": backtest.dataset_fingerprint,
                "strategy_version": selected_strategy.version,
                "engine_version": backtest.engine_version,
                "parameters": config.to_dict(),
                "cost_model": {"fee_bps": config.fee_bps, "slippage_bps": config.slippage_bps},
                "benchmark": config.benchmark,
                "timestamp": timestamp,
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
            "strategy_id": selected_strategy.strategy_id,
            "strategy_version": selected_strategy.version,
            "engine_version": backtest.engine_version,
            "config": config.to_dict(),
            "artifact_fingerprint": artifact.fingerprint,
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
    )
    quant_run = QuantRun.create(
        quant_run_id=identifier,
        research_run_id=research_run.run_id,
        dataset_version=backtest.dataset_fingerprint,
        strategy_version=selected_strategy.version,
        engine_version=backtest.engine_version,
        parameters={
            "strategy_id": selected_strategy.strategy_id,
            **config.to_dict(),
        },
        result_artifact=artifact,
        timestamp=timestamp,
    )
    return quant_run, research_run, report, backtest
