"""Typed experiment planning with explicit material-assumption review."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from finahinking.quant.validity import ResearchValidity, ValidityStatus

from .models import (
    AssumptionReview,
    EvaluationBoundary,
    ExperimentSpecification,
    Hypothesis,
    Period,
)

_MATERIAL_FIELDS = {"benchmark", "universe", "costs", "slippage", "optimization", "execution_timing", "parameters"}


def plan_experiment(
    hypothesis: Hypothesis,
    *,
    dataset_id: str,
    benchmark: str | None = None,
    universe: str | None = None,
    costs: Any = None,
    slippage: Any = None,
    optimization: bool = False,
    execution_timing: str | None = None,
    parameters: dict[str, Any] | None = None,
    assumptions_accepted: bool = False,
    tool_name: str = "quant.run_backtest",
) -> ExperimentSpecification:
    if not isinstance(hypothesis, Hypothesis):
        raise TypeError("hypothesis must be a Hypothesis")
    if tool_name not in {
        "quant.run_backtest", "quant.run_regression", "quant.evaluate_performance",
        "quant.analyze_risk", "quant.compare_benchmark", "quant.inspect_run",
    }:
        raise ValueError("tool_name is not allow-listed")
    resolved_benchmark = benchmark or str(hypothesis.benchmark)
    # A changed material choice is surfaced as a confirmation requirement.  It
    # is never silently substituted into the user's hypothesis.
    baseline_benchmark = str(hypothesis.benchmark)
    changed = benchmark is not None and resolved_benchmark != baseline_benchmark
    material = list(hypothesis.assumptions)
    changes: list[str] = []
    if changed:
        changes.append(f"benchmark: {baseline_benchmark} -> {resolved_benchmark}")
    if costs is not None:
        change = f"transaction costs: {costs}"
        material.append(change)
        changes.append(change)
        changed = True
    if slippage is not None:
        change = f"slippage: {slippage}"
        material.append(change)
        changes.append(change)
        changed = True
    if universe is not None and universe != str(hypothesis.universe):
        change = f"universe: {universe}"
        material.append(change)
        changes.append(change)
        changed = True
    if optimization:
        change = "parameter optimization requires explicit approval"
        material.append(change)
        changes.append(change)
        changed = True
    timing = execution_timing or "next_period"
    if execution_timing is not None and timing != "next_period":
        changes.append(f"execution timing: next_period -> {timing}")
        changed = True
    if parameters:
        changes.append("experiment parameters differ from the fixed default")
        material.append("experiment parameters differ from the fixed default")
        changed = True
    needs_confirmation = changed and not assumptions_accepted
    spec = ExperimentSpecification.from_hypothesis(hypothesis, dataset_id=dataset_id)
    # Keep the P5.5 boundary visible in the P6 plan.  This is metadata only;
    # the quant service still validates and executes its own OOSPlan.
    boundary = hypothesis.evaluation_boundary
    if boundary is None and isinstance(hypothesis.period, Period):
        # ISO date strings are sufficient for the deterministic fixture.  If a
        # domain-specific period cannot be split, leave the boundary explicit
        # as planned metadata rather than inventing dates.
        try:
            from datetime import date as _date

            start = _date.fromisoformat(hypothesis.period.start[:10])
            end = _date.fromisoformat(hypothesis.period.end[:10])
            days = max(2, (end - start).days)
            split = start.toordinal() + max(1, days // 2)
            train_end = _date.fromordinal(split).isoformat()
            boundary = EvaluationBoundary(
                test_period=Period(train_end, hypothesis.period.end),
                training_period=Period(hypothesis.period.start, train_end),
                method="later_test_window",
            )
        except (TypeError, ValueError, OverflowError):
            boundary = None
    review = AssumptionReview(
        accepted=bool(assumptions_accepted or not changed),
        assumptions=tuple(material),
        material_changes=tuple(changes),
    )
    validity_record = ResearchValidity.default_p5_5()
    statuses = {item.dimension: item.status for item in validity_record.assessments}
    if timing != "next_period":
        statuses["execution_timing"] = ValidityStatus.LIMITED
    if boundary is None:
        statuses["is_oos_separation"] = ValidityStatus.UNSUPPORTED
    validity = ResearchValidity.complete(
        statuses,
        warnings=validity_record.warnings,
        limitations=validity_record.limitations,
        multiple_testing=validity_record.multiple_testing,
    ).to_dict()
    return replace(
        spec,
        benchmark=resolved_benchmark,
        execution_timing=timing,
        material_assumptions=tuple(dict.fromkeys(material)),
        parameters=parameters or {},
        requires_confirmation=needs_confirmation,
        universe=universe or hypothesis.universe,
        factor=hypothesis.factor,
        period=hypothesis.period,
        evaluation_boundary=boundary,
        cost_model=costs if costs is not None else {"fee_bps": 5.0, "status": "default"},
        slippage_model=slippage if slippage is not None else {"slippage_bps": 5.0, "status": "default"},
        requested_metrics=("total_return", "volatility", "sharpe", "max_drawdown", "excess_return"),
        validity_profile=validity,
        oos_design={"method": "later_test_window", "boundary": boundary.to_dict() if boundary else None,
                    "status": "planned"},
        assumption_review=review,
        confirmation_reason="; ".join(dict.fromkeys(changes)) if changed else None,
        tool_name=tool_name,
    )


class ExperimentPlanner:
    def plan(self, hypothesis: Hypothesis, *, dataset_id: str, **kwargs: Any) -> ExperimentSpecification:
        return plan_experiment(hypothesis, dataset_id=dataset_id, **kwargs)


__all__ = ["ExperimentPlanner", "plan_experiment"]
