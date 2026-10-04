"""Constrained, deterministic hypothesis proposals."""

from __future__ import annotations

from typing import Any

from .classifier import classify_question
from .models import (
    Benchmark,
    EvaluationBoundary,
    Factor,
    Hypothesis,
    Period,
    ResearchQuestion,
    TaskCategory,
    Universe,
)


def build_hypothesis(question: ResearchQuestion | str, *, user_id: str | None = None, **overrides: Any) -> Hypothesis:
    """Build a falsifiable hypothesis without inventing a search procedure."""

    rq = question if isinstance(question, ResearchQuestion) else ResearchQuestion(str(question), user_id=user_id)
    classification = classify_question(rq)
    if classification.category is not TaskCategory.QUANT:
        raise ValueError("a hypothesis experiment is only available for QUANT questions")
    text = rq.question.casefold()
    if "momentum" in text:
        statement = "A fixed lagged momentum rank has positive excess return."
        null = "There is no excess return after costs."
        factor: Factor | str = Factor("cross_sectional_momentum", "Ranking of trailing returns measured before execution.", "r_t / r_{t-k} - 1")
        assumptions = ("fixed lookback", "next-period execution")
    elif "beta" in text or "sensitive" in text or "regression" in text:
        statement = "The asset has a measurable linear sensitivity to the benchmark."
        null = "The asset has zero benchmark sensitivity."
        factor = Factor("market_sensitivity", "Linear regression of asset returns on benchmark returns.")
        assumptions = ("returns are aligned by date", "benchmark is observed before fitting")
    else:
        statement = "The proposed factor is associated with next-period returns."
        null = "The factor has no association with next-period returns after costs."
        factor = Factor("user_specified_factor", "A fixed factor supplied by the research question.")
        assumptions = ("the factor definition is fixed before evaluation", "execution occurs in the next period")
    period = Period("2020-01-01", "2020-01-05")
    boundary = EvaluationBoundary(
        training_period=Period("2020-01-01", "2020-01-03"),
        test_period=Period("2020-01-03", "2020-01-05"),
    )
    values = {
        "statement": statement,
        "null_hypothesis": null,
        "universe": Universe("fixture_panel"),
        "period": period,
        "factor": factor,
        "benchmark": Benchmark("equal_weight"),
        "assumptions": assumptions,
        "limitations": ("liquidity not modeled", "historical evidence is not a forecast"),
        "evaluation_boundary": boundary,
        "hypothesis_id": f"hypothesis-{rq.fingerprint[:16]}",
        "version": 1,
        "user_claim": rq.question,
    }
    values.update(overrides)
    return Hypothesis(question=rq, **values)


def validate_hypothesis(hypothesis: Hypothesis, question: ResearchQuestion | str | None = None) -> Hypothesis:
    if not isinstance(hypothesis, Hypothesis):
        raise TypeError("hypothesis must be a Hypothesis")
    if question is not None:
        expected = question.question if isinstance(question, ResearchQuestion) else str(question)
        if hypothesis.question.question != expected:
            raise ValueError("hypothesis does not preserve the research question")
    if hypothesis.statement_type != "SYSTEM HYPOTHESIS":
        raise ValueError("hypothesis statement type must be SYSTEM HYPOTHESIS")
    return hypothesis


HypothesisBuilder = build_hypothesis

__all__ = ["HypothesisBuilder", "build_hypothesis", "validate_hypothesis"]
