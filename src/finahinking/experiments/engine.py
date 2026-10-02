from __future__ import annotations

from dataclasses import replace

from finahinking.data.models import Dataset
from finahinking.data.validation import validate_price_dataset
from finahinking.factors.core import FactorDefinition, evaluate_factor

from .models import ResearchRun


class ReproducibilityError(ValueError):
    """Raised when an experiment cannot reproduce its recorded evidence."""


class ExperimentEngine:
    def execute(
        self,
        question: str,
        hypothesis: str,
        dataset: Dataset,
        factor: FactorDefinition,
        horizon: int,
        conclusion: str,
        insight: str,
        run_id: str | None = None,
        created_at: str | None = None,
    ) -> ResearchRun:
        if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1:
            raise ValueError("horizon must be a positive integer")
        frame = validate_price_dataset(dataset.frame, "close")
        prices = frame["close"]
        factor_values = factor.compute(prices)
        forward_returns = prices.pct_change(horizon).shift(-horizon)
        result = evaluate_factor(factor_values, forward_returns, shift_periods=1)
        limitations = [factor.limitations, "Forward-return association is descriptive evidence, not advice."]
        return ResearchRun.create(
            question=question,
            hypothesis=hypothesis,
            dataset=dataset,
            factor=factor,
            method="information_coefficient",
            parameters={"horizon": horizon, "factor_shift_periods": 1},
            result=result,
            conclusion=conclusion,
            insight=insight,
            limitations=limitations,
            run_id=run_id,
            created_at=created_at,
        )

    def reproduce(self, run: ResearchRun, dataset: Dataset, factor: FactorDefinition) -> ResearchRun:
        candidate_metadata = ResearchRun.create(
            question="q",
            hypothesis="h",
            dataset=dataset,
            factor=factor,
            method=run.method,
            parameters={},
            result={},
            conclusion="c",
            insight="i",
            limitations=[],
        )
        if run.dataset_fingerprint != candidate_metadata.dataset_fingerprint:
            raise ReproducibilityError("dataset fingerprint does not match recorded run")
        if factor.name != run.factor_name:
            raise ReproducibilityError("factor definition does not match recorded run")
        candidate = self.execute(
            run.question,
            run.hypothesis,
            dataset,
            factor,
            int(run.parameters["horizon"]),
            run.conclusion,
            run.insight,
            run_id=run.run_id,
            created_at=run.created_at,
        )
        if candidate.result_fingerprint != run.result_fingerprint:
            raise ReproducibilityError("result fingerprint does not match recorded run")
        return replace(candidate)
