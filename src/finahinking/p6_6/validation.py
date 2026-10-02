"""OOS, walk-forward, and multiple-testing diagnostics for P6.6."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from finahinking.quant.splits import OOSPlan, OOSResult, Period, evaluate_oos

from .models import digest


@dataclass(frozen=True)
class MultipleTestingSummary:
    hypothesis: str
    experiment_count: int
    search_space: Mapping[str, Any]
    selection_method: str
    adjustment: str
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "hypothesis": self.hypothesis,
            "experiment_count": self.experiment_count,
            "search_space": dict(self.search_space),
            "selection_method": self.selection_method,
            "adjustment": self.adjustment,
            "warnings": list(self.warnings),
        }
        return {**payload, "fingerprint": digest(payload)}


@dataclass(frozen=True)
class WalkForwardWindow:
    index: int
    plan: OOSPlan
    result: OOSResult
    frozen_configuration: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "plan": self.plan.to_dict(),
            "result": self.result.to_dict(),
            "frozen_configuration": dict(self.frozen_configuration),
        }


@dataclass(frozen=True)
class WalkForwardReport:
    windows: tuple[WalkForwardWindow, ...]
    multiple_testing: MultipleTestingSummary
    limitations: tuple[str, ...] = (
        "Walk-forward aggregation is descriptive and does not establish future performance.",
        "Window results inherit source, universe, liquidity, and corporate-action limitations.",
    )

    def to_dict(self) -> dict[str, Any]:
        payload = {"windows": [item.to_dict() for item in self.windows], "multiple_testing": self.multiple_testing.to_dict(), "limitations": list(self.limitations)}
        return {**payload, "fingerprint": digest(payload)}


def make_oos_plan(
    training: Period,
    test: Period,
    *,
    validation: Period | None = None,
    hypothesis: str,
    search_space: Mapping[str, Any] | None = None,
    experiment_count: int = 1,
    frozen_configuration: Mapping[str, Any],
) -> OOSPlan:
    plan = OOSPlan(
        training=training,
        validation=validation,
        test=test,
        hypothesis=hypothesis,
        search_space=dict(search_space or {}),
        experiment_count=experiment_count,
    )
    return plan.freeze_configuration(frozen_configuration)


def evaluate_frozen_oos(plan: OOSPlan, observations: Mapping[Any, float]) -> OOSResult:
    return evaluate_oos(plan, observations)


def walk_forward(
    windows: Sequence[tuple[OOSPlan, Mapping[Any, float], Mapping[str, Any]]],
    *,
    hypothesis: str,
    search_space: Mapping[str, Any] | None = None,
    experiment_count: int | None = None,
    selection_method: str = "pre_specified",
) -> WalkForwardReport:
    """Aggregate pre-frozen windows; it never chooses parameters itself."""
    records: list[WalkForwardWindow] = []
    for index, (plan, observations, configuration) in enumerate(windows):
        if plan.evaluation_boundary is None or plan.parameter_selection_boundary.frozen_configuration is None:
            raise ValueError("every walk-forward plan must be frozen before evaluation")
        result = evaluate_oos(plan, observations)
        if result.configuration_fingerprint != plan.frozen_configuration_fingerprint:
            raise ValueError("OOS result configuration does not match the frozen plan")
        records.append(WalkForwardWindow(index, plan, result, dict(configuration)))
    count = experiment_count if experiment_count is not None else len(records)
    if count < len(records):
        raise ValueError("experiment_count cannot be below observed windows")
    summary = MultipleTestingSummary(
        hypothesis=hypothesis,
        experiment_count=count,
        search_space=dict(search_space or {}),
        selection_method=selection_method,
        adjustment="report_only; no p-value correction is claimed by this descriptive slice",
        warnings=("Multiple-testing metadata is recorded; selection bias remains possible.",),
    )
    return WalkForwardReport(tuple(records), summary)


__all__ = ["MultipleTestingSummary", "WalkForwardReport", "WalkForwardWindow", "evaluate_frozen_oos", "make_oos_plan", "walk_forward"]
