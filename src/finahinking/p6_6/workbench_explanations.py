"""Evidence-bound explanation bundles for workbench parameter changes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .workbench import ParameterChangeExplanation, _safe
from .workbench_engine import WorkbenchRun

_TRACE_LIBRARY: dict[str, dict[str, str]] = {
    "momentum": {
        "concept": "Lagged relative price movement",
        "intuition": "Compare recent strength while keeping the signal behind the information boundary.",
        "math": "m_t = P_(t-1) / P_(t-L-1) - 1",
        "derivation": "Use the close at t-1, divide by the close L periods earlier, then subtract one.",
        "code": "feature graph: return → rolling(L) → lag(1)",
        "finance": "A larger horizon changes the holding period and may change turnover and regime exposure.",
        "parameter": "Increasing L usually smooths short-term noise but can delay reversals.",
        "result": "Compare signal, selection, weight, risk, and cost fields in the paired run.",
        "assumptions": "available_at is no later than signal time; the universe is point-in-time approved.",
    },
    "lag": {
        "concept": "Information availability boundary",
        "intuition": "A signal may only use information that was available before the decision timestamp.",
        "math": "x_signal(t) = x_observed(t-1)",
        "derivation": "Shift the observed feature by one decision period before mapping it to a target.",
        "code": "IR node: lag(1)",
        "finance": "The lag changes entry timing and prevents same-close look-ahead.",
        "parameter": "Removing the lag invalidates the experiment rather than improving it.",
        "result": "The engine records target and held weight separately so timing is visible.",
        "assumptions": "The source timestamp and available_at field are trustworthy.",
    },
    "weights": {
        "concept": "Signal-to-capital mapping",
        "intuition": "A score is not a position; a policy decides how much capital it may request.",
        "math": "w_i = min(cap_i, scale × mapping(score_i))",
        "derivation": "Map eligible scores, cap each asset, then project total exposure and cash buffer.",
        "code": "policy: mapping → cap → exposure projection",
        "finance": "The mapping changes concentration, turnover, and sensitivity to winners.",
        "parameter": "A tighter cap lowers concentration but can leave more cash or increase reallocation.",
        "result": "Inspect raw_weight, risk_scale, final_weight, held_weight, and cash together.",
        "assumptions": "First version is long-only and total exposure is at most one.",
    },
    "costs": {
        "concept": "Implementation friction",
        "intuition": "Every change of position consumes fees and assumed slippage.",
        "math": "net = gross - |Δw| × (fee_bps + slippage_bps) / 10000",
        "derivation": "Measure the delayed holding return, then subtract deterministic cost components.",
        "code": "execution: delay → trade → fee/slippage",
        "finance": "A fragile signal can disappear after turnover and execution assumptions.",
        "parameter": "Higher costs penalize frequent resizing and make stable regions more valuable.",
        "result": "The report keeps fees, slippage, turnover, blocked trades, and net return visible.",
        "assumptions": "Costs are illustrative historical assumptions, not a live market-impact estimate.",
    },
    "risk": {
        "concept": "State-dependent risk overlay",
        "intuition": "Risk conditions change how much of a valid signal can be held.",
        "math": "risk_scale = min(1, target_volatility / realized_volatility)",
        "derivation": "Estimate the bounded realized-volatility proxy, compare it with the target, and apply the state multiplier.",
        "code": "risk state → scale → allowed action",
        "finance": "The overlay can reduce exposure without rewriting the factor definition.",
        "parameter": "Thresholds and hysteresis trade responsiveness against state chattering.",
        "result": "Each point records the state, reasons, allowed actions, and resulting scale.",
        "assumptions": "Volatility is a diagonal approximation and cannot replace a full covariance model.",
    },
    "oos": {
        "concept": "Out-of-sample separation",
        "intuition": "A result used to choose a parameter is not independent evidence for that choice.",
        "math": "train → validation → test, with test opened only after freeze",
        "derivation": "Freeze the charter and candidate before reading test/OOS results.",
        "code": "research charter: test_accessible=False until explicit freeze",
        "finance": "The boundary reduces false confidence from repeated search, but cannot remove regime change.",
        "parameter": "Parameter search budgets and all failed attempts remain visible.",
        "result": "This local replay is descriptive; OOS status stays explicit until a frozen evaluation exists.",
        "assumptions": "The dataset split is point-in-time and the evaluation rule was declared in advance.",
    },
}


def _trace(component: str, change: Mapping[str, Any], run: WorkbenchRun) -> dict[str, Any]:
    base = dict(_TRACE_LIBRARY.get(component, _TRACE_LIBRARY["weights"]))
    base["parameter"] = f"{base['parameter']} Change under review: {dict(change) if change else 'no explicit change'}"
    base["result"] = f"{base['result']} Run fingerprint: {run.fingerprint[:16]}…"
    return base


def _metrics(value: Mapping[str, Any] | None, fallback: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in (value or fallback).items()}


def build_explanation_package(
    run: WorkbenchRun,
    *,
    strategy_id: str,
    parameter_changes: Mapping[str, Mapping[str, Any]],
    intent: str,
    formula_before: str,
    formula_after: str,
    code_trace: Sequence[str] = (),
    baseline_metrics: Mapping[str, Any] | None = None,
    variant_metrics: Mapping[str, Any] | None = None,
    next_experiment: str = "Compare an adjacent parameter while holding the remaining policy fixed.",
) -> dict[str, Any]:
    if not isinstance(run, WorkbenchRun):
        raise TypeError("run must be a WorkbenchRun")
    if not parameter_changes:
        raise ValueError("parameter_changes cannot be empty")
    baseline = _metrics(baseline_metrics, run.metrics)
    variant = _metrics(variant_metrics, run.metrics)
    delta = {key: round(variant[key] - baseline[key], 12) for key in baseline.keys() & variant.keys() if isinstance(baseline[key], (int, float)) and isinstance(variant[key], (int, float))}
    components = tuple(dict.fromkeys(code_trace or ("momentum", "lag", "weights", "risk", "costs", "oos")))
    limitations = list(run.limitations)
    attribution_status = "ATTRIBUTION_CONFOUNDED" if len(parameter_changes) > 1 else "ATTRIBUTION_AVAILABLE"
    if attribution_status == "ATTRIBUTION_CONFOUNDED":
        limitations.append("Single-parameter causality is unavailable because multiple parameters changed together.")
    attribution = {"status": attribution_status, "delta": delta, "method": "paired baseline/variant descriptive comparison"}
    explanation = ParameterChangeExplanation(
        explanation_id=f"explanation-{run.run_id}",
        strategy_id=strategy_id,
        parameter_changes=parameter_changes,
        intent=intent,
        formula_before=formula_before,
        formula_after=formula_after,
        derivation=("Read the frozen signal definition.", "Apply the declared policy mapping.", "Compare delayed holdings, risk, and costs."),
        code_trace=tuple(components),
        finance_interpretation="This package describes a historical paper-research replay; it does not recommend an order.",
        expected_effects=("signal selection may change", "position concentration may change", "cost and drawdown may change"),
        paired_metrics={"baseline": baseline, "variant": variant},
        attribution=attribution,
        oos_status="NOT_EVALUATED",
        stress_status="NOT_EVALUATED",
        stability_status="UNKNOWN",
        assumptions=("The dataset fingerprint and policy fingerprints are held fixed within each run.", "The browser does not recompute financial values."),
        limitations=tuple(limitations),
        next_experiment=next_experiment,
    )
    payload = {"schema_version": 1, "paper_only": True, "traces": {component: _trace(component, parameter_changes.get(component, {}), run) for component in components}, "parameter_change": explanation.to_dict(), "evidence": {"run_id": run.run_id, "run_fingerprint": run.fingerprint, "dataset_fingerprint": run.dataset_fingerprint, "strategy_fingerprint": run.strategy_fingerprint, "policy_fingerprints": {key: value.get("policy_id") for key, value in run.policies.items()}}, "limitations": tuple(limitations), "next_experiment": next_experiment}
    return _safe(payload)


__all__ = ["build_explanation_package"]
