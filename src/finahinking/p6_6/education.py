"""Safe educational code, math/finance traceability, and learning cards."""

from __future__ import annotations

import ast
import hashlib
from dataclasses import dataclass
from typing import Any

from finahinking.p6.learning import LearningCard, make_learning_card

from .models import StrategyIR, StrategySpec


@dataclass(frozen=True)
class CodeSafetyReport:
    safe: bool
    violations: tuple[str, ...]
    source_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return {"safe": self.safe, "violations": list(self.violations), "source_fingerprint": self.source_fingerprint}

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


@dataclass(frozen=True)
class StrategyLearningTrace:
    component: str
    code: str
    math: str
    finance: str
    strategy_role: str
    assumption: str
    limitation: str
    input_example: str = ""
    output_example: str = ""

    # Verbose aliases make the trace self-documenting for export consumers
    # while preserving the concise fields used by the existing P6 contracts.
    @property
    def component_id(self) -> str:
        return self.component

    @property
    def code_explanation(self) -> str:
        return self.code

    @property
    def math_explanation(self) -> str:
        return self.math

    @property
    def finance_explanation(self) -> str:
        return self.finance

    def to_dict(self) -> dict[str, str]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class EducationalCode:
    source: str
    safety: CodeSafetyReport
    traces: tuple[StrategyLearningTrace, ...]
    strategy_id: str
    strategy_version: str

    @property
    def source_fingerprint(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "safety": self.safety.to_dict(), "traces": [trace.to_dict() for trace in self.traces], "strategy_id": self.strategy_id, "strategy_version": self.strategy_version, "source_fingerprint": self.source_fingerprint}


_FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "open", "input", "globals", "locals", "getattr", "setattr", "delattr"}
_FORBIDDEN_MODULES = {"os", "subprocess", "socket", "pathlib", "sys", "importlib", "requests", "urllib", "httpx", "boto3", "broker", "ibkr", "alpaca"}


def scan_educational_code(source: str) -> CodeSafetyReport:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source is required")
    violations: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        violations.append(f"syntax:{exc.msg}")
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                violations.append("imports are not permitted in educational code")
            elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
                violations.append(f"forbidden name: {node.id}")
            elif isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_NAMES:
                violations.append(f"forbidden attribute: {node.attr}")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_MODULES:
                violations.append(f"forbidden call: {node.func.id}")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                lowered = node.value.lower()
                if any(term in lowered for term in ("api_key", "secret", "password", "credential", "broker_order")):
                    violations.append("credential or broker text is not permitted")
    ordered = tuple(dict.fromkeys(violations))
    return CodeSafetyReport(not ordered, ordered, hashlib.sha256(source.encode("utf-8")).hexdigest())


def validate_generated_code(source: str) -> CodeSafetyReport:
    return scan_educational_code(source)


def _traces(spec: StrategySpec) -> tuple[StrategyLearningTrace, ...]:
    template = str(spec.parameters.get("template", ""))
    common = (
        StrategyLearningTrace("lag", "series.shift(1)", "x_t uses information through t-1", "Lagging prevents trading on information that was not available at the signal close.", "Protect the research from look-ahead bias.", "The source timestamps and available_at field are trustworthy.", "Bad timestamps can still invalidate the claim."),
        StrategyLearningTrace("rolling_window", "series.rolling(window=20)", "A rolling statistic summarizes the trailing 20 observations.", "A finite window adapts to recent conditions but can be noisy.", "Define the information horizon for the signal.", "Twenty observations are enough for the chosen statistic.", "Changing the window creates a new feature version."),
        StrategyLearningTrace("weights", "target_weight = condition.astype(float) * target", "Weights map a condition into a bounded portfolio exposure.", "A target weight controls capital allocation rather than predicting a return.", "Construct a long-only, capped position.", "The target is fully invested only when the condition holds.", "A target weight is not a guarantee of execution."),
        StrategyLearningTrace("costs", "turnover * (fee_bps + slippage_bps) / 10000", "Costs reduce equity when positions change.", "Fees and slippage are friction assumptions, not observed future costs.", "Prevent frictionless backtest overstatement.", "The configured bps are applied deterministically.", "Real execution can differ materially."),
        StrategyLearningTrace("oos", "train -> validation -> test", "Out-of-sample evaluation keeps the final period untouched during fitting.", "OOS evidence is weaker than a prospective live observation.", "Separate discovery from evaluation.", "The split dates are frozen before interpretation.", "Multiple testing and regime change remain risks."),
    )
    if template == "lagged_momentum_low_volatility":
        return common + (
            StrategyLearningTrace("momentum", "close.pct_change(20).shift(1)", "m_t = P_(t-1) / P_(t-21) - 1", "Momentum measures trailing price strength.", "Rank assets before selecting a portfolio.", "Past relative strength may persist briefly.", "Momentum can reverse and is sensitive to costs."),
            StrategyLearningTrace("low_volatility", "volatility <= threshold", "s_t <= c", "A volatility filter excludes the high-variability tail.", "Reduce exposure to the most volatile candidates.", "The threshold is selected before OOS interpretation.", "A lower realized volatility is not lower total risk."),
            StrategyLearningTrace("ranking", "rank(momentum, scope='date')", "Percentile rank compares assets on the same date.", "Cross-sectional ranking makes selection relative to the available universe.", "Choose the top eligible candidates.", "The universe is approved and point-in-time.", "Universe changes can create selection bias."),
        )
    return common + (
        StrategyLearningTrace("moving_average", "close.rolling(20).mean().shift(1)", "MA_t = mean(P_(t-20), ..., P_(t-1))", "The moving average smooths recent prices.", "Compare current price with a lagged trend baseline.", "Trend persistence may make the condition useful.", "Moving averages lag reversals."),
        StrategyLearningTrace("drawdown", "equity / equity.cummax() - 1", "DD_t = V_t / max(V_0..V_t) - 1", "Drawdown measures loss from the running equity peak.", "Expose path risk even when terminal returns look attractive.", "Equity values include configured costs.", "Historical drawdown is not a loss limit."),
    )


def generate_educational_code(spec: StrategySpec, ir: StrategyIR) -> EducationalCode:
    if not spec.reviewed:
        raise ValueError("educational code requires a reviewed StrategySpec")
    if ir.strategy_version.spec.fingerprint != spec.fingerprint:
        raise ValueError("IR and StrategySpec do not match")
    template = str(spec.parameters.get("template", ""))
    trace_lines = [f"# trace:{trace.component}" for trace in _traces(spec)]
    if template == "lagged_momentum_low_volatility":
        body = """def calculate_features(frame):
    # trace:momentum
    momentum = frame[\"close\"].pct_change(20).shift(1)
    # trace:low_volatility
    volatility = frame[\"close\"].pct_change().rolling(20).std() * (252 ** 0.5)
    volatility = volatility.shift(1)
    # trace:ranking
    rank = momentum.rank(pct=True)
    return {\"momentum\": momentum, \"volatility\": volatility, \"rank\": rank}


def target_weight(features, volatility_threshold=0.60, target_weight=0.75):
    # trace:weights
    eligible = (features[\"volatility\"] <= volatility_threshold)
    return (eligible & (features[\"momentum\"] > 0)).astype(float) * target_weight
"""
    elif template == "moving_average_trend":
        body = """def calculate_features(frame):
    # trace:moving_average
    moving_average = frame[\"close\"].rolling(20).mean().shift(1)
    return {\"moving_average\": moving_average}


def target_weight(features, close, target=0.75):
    # trace:weights
    return (close > features[\"moving_average\"]).astype(float) * target
"""
    else:
        raise ValueError(f"unsupported strategy template: {template}")
    source = "\n".join(trace_lines[:0]) + body + "\n# Educational only: execution remains in the governed P5 engine.\n"
    safety = scan_educational_code(source)
    if not safety.safe:
        raise ValueError(f"generated educational code failed safety scan: {safety.violations}")
    return EducationalCode(source, safety, _traces(spec), spec.strategy_id, spec.version)


def learning_cards(spec: StrategySpec, ir: StrategyIR, *, evidence_reference: str | None = None) -> tuple[LearningCard, ...]:
    code = generate_educational_code(spec, ir)
    evidence = evidence_reference or f"strategy:{spec.strategy_id}:{spec.version}"
    cards: list[LearningCard] = []
    for trace in code.traces:
        cards.append(make_learning_card(concept=trace.component, definition=trace.math, formula=trace.code, result_context={"evidence_reference": evidence, "strategy_id": spec.strategy_id, "strategy_version": spec.version, "interpretation": trace.finance}, limitation=trace.limitation, evidence_reference=evidence, common_misconception="Historical evidence is not a promise of future returns."))
    return tuple(cards)


__all__ = ["CodeSafetyReport", "EducationalCode", "StrategyLearningTrace", "generate_educational_code", "learning_cards", "scan_educational_code", "validate_generated_code"]
