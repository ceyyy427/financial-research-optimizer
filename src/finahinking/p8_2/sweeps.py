"""Finathink-native, deterministic parameter sensitivity sweeps."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any

from .contracts import ParameterSweepSpecification, SweepResult, _payload


def _evaluate(evaluator: Callable[..., Any], parameters: dict[str, Any]) -> Any:
    """Call a bounded evaluator without allowing it to receive hidden state."""

    signature = inspect.signature(evaluator)
    positional = [
        item
        for item in signature.parameters.values()
        if item.kind in (item.POSITIONAL_ONLY, item.POSITIONAL_OR_KEYWORD)
    ]
    if not positional and not any(item.kind is item.VAR_POSITIONAL for item in signature.parameters.values()):
        return evaluator()
    return evaluator(dict(parameters))


def _normalize_experiment(parameters: Mapping[str, Any], value: Any, index: int) -> dict[str, Any]:
    if isinstance(value, Mapping):
        normalized = _payload(value)
    else:
        normalized = {"oos": {"score": float(value)}}
    normalized["parameters"] = _payload(parameters)
    normalized["experiment_id"] = f"experiment-{index + 1:04d}"
    normalized.setdefault("status", "COMPLETE")
    # Keep explicit split labels even when a simple evaluator returns a flat
    # metric mapping.  This prevents a chart/UI from implying in-sample data
    # was evaluated out of sample.
    if "oos" not in normalized:
        normalized["oos"] = {}
    if "train" not in normalized:
        normalized["train"] = {}
    if "validation" not in normalized:
        normalized["validation"] = {}
    return normalized


def _failed_experiment(parameters: Mapping[str, Any], index: int, error: Exception) -> dict[str, Any]:
    """Keep a bounded, inspectable record when one grid cell cannot run."""

    message = str(error).strip()[:256] or "evaluator failed without a message"
    return {
        "parameters": _payload(parameters),
        "experiment_id": f"experiment-{index + 1:04d}",
        "status": "FAILED",
        "error": {"type": type(error).__name__, "message": message},
        "train": {},
        "validation": {},
        "oos": {},
    }


def _regions(experiments: tuple[dict[str, Any], ...]) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    scores: list[tuple[float, dict[str, Any]]] = []
    for item in experiments:
        oos = item.get("oos")
        score = oos.get("score") if isinstance(oos, Mapping) else None
        try:
            if score is not None:
                scores.append((float(score), item))
        except (TypeError, ValueError):
            continue
    if len(scores) < 2:
        return (), ()
    ordered = sorted(scores, key=lambda item: (item[0], item[1]["experiment_id"]))
    low = ordered[0][0]
    high = ordered[-1][0]
    spread = high - low
    if spread <= 0:
        return tuple({"parameters": dict(item[1]["parameters"]), "reason": "equal OOS score"} for item in ordered), ()
    robust = tuple(
        {"parameters": dict(item["parameters"]), "oos_score": score, "classification": "robust-region"}
        for score, item in ordered
        if score >= low + spread * 0.75
    )
    unstable = tuple(
        {"parameters": dict(item["parameters"]), "oos_score": score, "classification": "unstable-region"}
        for score, item in ordered
        if score < low + spread * 0.25
    )
    return robust, unstable


def run_parameter_sweep(
    spec: ParameterSweepSpecification,
    evaluator: Callable[[dict[str, Any]], Mapping[str, Any] | float],
) -> SweepResult:
    """Evaluate every declared combination in deterministic grid order.

    The function records all experiments and diagnostics.  It never selects or
    labels a winning strategy; consumers must inspect robustness and OOS
    context themselves.
    """

    if not isinstance(spec, ParameterSweepSpecification):
        raise TypeError("spec must be a ParameterSweepSpecification")
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    records_list: list[dict[str, Any]] = []
    for index, parameters in enumerate(spec.enumerate_parameters()):
        try:
            value = _evaluate(evaluator, parameters)
            records_list.append(_normalize_experiment(parameters, value, index))
        except Exception as exc:  # noqa: BLE001 - every grid cell remains auditable
            records_list.append(_failed_experiment(parameters, index, exc))
    records = tuple(records_list)
    robust, unstable = _regions(records)
    warning = (
        f"Multiple-testing context: {len(records)} parameter experiments were evaluated; "
        "selection bias remains possible."
    )
    comparison = tuple(
        {
            "experiment_id": item["experiment_id"],
            "parameters": dict(item["parameters"]),
            "oos": item.get("oos", {}),
            "scope": "OOS",
        }
        for item in records
    )
    status = "PARTIAL" if any(item.get("status") in {"FAILED", "PENDING"} for item in records) else "COMPLETE"
    return SweepResult(
        specification_fingerprint=spec.fingerprint,
        experiments=records,
        warnings=(warning, "OOS values are descriptive and do not establish future performance."),
        multiple_testing={
            "experiment_count": len(records),
            "selection_policy": spec.selection_policy,
            "adjustment": "report_only",
            "warning": warning,
        },
        robust_regions=robust,
        unstable_regions=unstable,
        oos_comparison=comparison,
        status=status,
    )


__all__ = ["run_parameter_sweep"]
