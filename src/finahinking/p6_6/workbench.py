"""Immutable contracts for the factor–strategy workbench.

The workbench keeps signal, sizing, risk, execution, and explanation as
separate data-only boundaries.  These objects never execute model output or
broker operations; they describe a bounded paper-research experiment.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SECRET = re.compile(r"(?i)(api[_-]?key|token|secret|password|private[_-]?key)\s*[=:]")
_PATH = re.compile(r"(?:/Users/|/home/|[A-Za-z]:[\\/])")
_EXECUTABLE = re.compile(r"(?i)(?:^|[_-])(code|python|shell|bash|sql|command|broker|order|network|url)(?:$|[_-])")

POSITION_MAPPINGS = frozenset({"equal_weight", "rank_weight", "inverse_volatility", "risk_budget"})
RISK_STATES = ("NORMAL", "CAUTION", "DEFENSIVE", "FREEZE", "FLATTEN", "RECOVERY")
ALLOWED_RISK_ACTIONS = frozenset({"SKIP", "REDUCE", "FREEZE", "FLATTEN", "FALLBACK"})
ALLOWED_FAULT_ACTIONS = frozenset({"SKIP", "REDUCE", "FREEZE", "FLATTEN", "FALLBACK", "BLOCK"})


def _id(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or not _IDENTIFIER.fullmatch(value.strip()):
        raise ValueError(f"{field_name} is invalid")
    return value.strip()


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return _safe(value.strip(), field_name)


def _finite(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite")
    return result


def _safe(value: Any, path: str = "payload") -> Any:
    if callable(value):
        raise TypeError(f"{path} cannot contain executable values")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} must be finite")
    if isinstance(value, str):
        if _SECRET.search(value) or _PATH.search(value):
            raise ValueError(f"{path} contains a secret or absolute path")
        return value
    if isinstance(value, Mapping):
        return {str(key): _safe(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_safe(item, f"{path}[]") for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        return _safe(value.item(), path)
    raise TypeError(f"{path} contains unsupported value type {type(value).__name__}")


def _freeze(value: Mapping[str, Any] | None, field_name: str) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    def immutable(item: Any) -> Any:
        if isinstance(item, dict):
            return MappingProxyType({key: immutable(child) for key, child in item.items()})
        if isinstance(item, list):
            return tuple(immutable(child) for child in item)
        return item
    return immutable(_safe(value, field_name))


def _tuple_text(value: Sequence[str] | None, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{field_name} must be a sequence")
    return tuple(_text(item, field_name) for item in value)


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class _Fingerprint:
    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True, slots=True)
class PositionPolicySpec(_Fingerprint):
    policy_id: str
    version: str
    mapping: str
    target_volatility: float | None = None
    max_single_weight: float = 1.0
    max_exposure: float = 1.0
    cash_buffer: float = 0.0
    max_turnover: float = 1.0
    max_trade_weight: float = 1.0
    liquidity_participation: float = 0.1
    long_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _id(self.policy_id, "policy_id"))
        object.__setattr__(self, "version", _id(self.version, "version"))
        if self.mapping not in POSITION_MAPPINGS:
            raise ValueError(f"mapping must be one of {sorted(POSITION_MAPPINGS)}")
        for field_name in ("max_single_weight", "max_exposure", "cash_buffer", "max_turnover", "max_trade_weight", "liquidity_participation"):
            number = _finite(getattr(self, field_name), field_name)
            if number < 0:
                raise ValueError(f"{field_name} must be non-negative")
            object.__setattr__(self, field_name, number)
        if self.max_single_weight > 1 or self.max_exposure > 1 or self.cash_buffer > 1 or self.liquidity_participation > 1:
            raise ValueError("position limits must be between 0 and 1")
        if self.target_volatility is not None:
            target = _finite(self.target_volatility, "target_volatility")
            if target <= 0:
                raise ValueError("target_volatility must be positive")
            object.__setattr__(self, "target_volatility", target)
        if not isinstance(self.long_only, bool):
            raise TypeError("long_only must be boolean")
        if not self.long_only:
            raise ValueError("first-version position policies are long-only")

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, "version": self.version, "mapping": self.mapping, "target_volatility": self.target_volatility, "max_single_weight": self.max_single_weight, "max_exposure": self.max_exposure, "cash_buffer": self.cash_buffer, "max_turnover": self.max_turnover, "max_trade_weight": self.max_trade_weight, "liquidity_participation": self.liquidity_participation, "long_only": self.long_only}


@dataclass(frozen=True, slots=True)
class RiskStatePolicy(_Fingerprint):
    policy_id: str
    version: str
    thresholds: Mapping[str, Any] = field(default_factory=dict)
    hysteresis: float = 0.02
    minimum_duration: int = 1
    actions: Mapping[str, Sequence[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _id(self.policy_id, "policy_id"))
        object.__setattr__(self, "version", _id(self.version, "version"))
        thresholds = dict(self.thresholds) or {"caution_volatility": 0.18, "defensive_volatility": 0.26, "freeze_drawdown": 0.20, "recovery_drawdown": 0.05}
        normalized = {str(key): _finite(value, f"thresholds.{key}") for key, value in thresholds.items()}
        if any(value < 0 for value in normalized.values()):
            raise ValueError("risk thresholds must be non-negative")
        object.__setattr__(self, "thresholds", MappingProxyType(normalized))
        hysteresis = _finite(self.hysteresis, "hysteresis")
        if hysteresis < 0:
            raise ValueError("hysteresis must be non-negative")
        object.__setattr__(self, "hysteresis", hysteresis)
        if isinstance(self.minimum_duration, bool) or int(self.minimum_duration) < 1:
            raise ValueError("minimum_duration must be a positive integer")
        object.__setattr__(self, "minimum_duration", int(self.minimum_duration))
        defaults = {"NORMAL": ("SKIP",), "CAUTION": ("REDUCE",), "DEFENSIVE": ("REDUCE", "FREEZE"), "FREEZE": ("FREEZE",), "FLATTEN": ("FLATTEN",), "RECOVERY": ("FALLBACK",)}
        raw_actions = dict(self.actions) or defaults
        normalized_actions: dict[str, tuple[str, ...]] = {}
        for state, actions in raw_actions.items():
            if state not in RISK_STATES:
                raise ValueError(f"unknown risk state: {state}")
            values = tuple(actions) if not isinstance(actions, str) else (actions,)
            if not values or any(action not in ALLOWED_RISK_ACTIONS for action in values):
                raise ValueError(f"action for {state} is not allow-listed")
            normalized_actions[state] = values
        object.__setattr__(self, "actions", MappingProxyType(normalized_actions))

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, "version": self.version, "thresholds": dict(self.thresholds), "hysteresis": self.hysteresis, "minimum_duration": self.minimum_duration, "actions": {state: list(actions) for state, actions in self.actions.items()}}


@dataclass(frozen=True, slots=True)
class ExecutionPolicy(_Fingerprint):
    policy_id: str
    version: str
    fee_bps: float = 5.0
    slippage_bps: float = 5.0
    stress_slippage_bps: float = 15.0
    delay_periods: int = 1
    rebalance_band: float = 0.0
    minimum_trade_weight: float = 0.0
    liquidity_participation: float = 0.1

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _id(self.policy_id, "policy_id"))
        object.__setattr__(self, "version", _id(self.version, "version"))
        for field_name in ("fee_bps", "slippage_bps", "stress_slippage_bps", "rebalance_band", "minimum_trade_weight", "liquidity_participation"):
            value = _finite(getattr(self, field_name), field_name)
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
            object.__setattr__(self, field_name, value)
        if self.liquidity_participation > 1:
            raise ValueError("liquidity_participation must be between 0 and 1")
        if isinstance(self.delay_periods, bool) or int(self.delay_periods) < 1 or int(self.delay_periods) != self.delay_periods:
            raise ValueError("delay_periods must be a positive integer; same-period fills are forbidden")
        object.__setattr__(self, "delay_periods", int(self.delay_periods))

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, "version": self.version, "fee_bps": self.fee_bps, "slippage_bps": self.slippage_bps, "stress_slippage_bps": self.stress_slippage_bps, "delay_periods": self.delay_periods, "rebalance_band": self.rebalance_band, "minimum_trade_weight": self.minimum_trade_weight, "liquidity_participation": self.liquidity_participation}


@dataclass(frozen=True, slots=True)
class FaultPolicy(_Fingerprint):
    policy_id: str
    version: str
    actions: Mapping[str, str] = field(default_factory=dict)
    retry_limit: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _id(self.policy_id, "policy_id"))
        object.__setattr__(self, "version", _id(self.version, "version"))
        defaults = {"DATA_STALE": "SKIP", "FACTOR_FAILURE": "SKIP", "SLIPPAGE_EXCEEDED": "REDUCE", "CASH_LIMIT": "REDUCE", "COMPUTE_TIMEOUT": "FREEZE", "RISK_BUDGET": "FREEZE"}
        actions = dict(self.actions) or defaults
        if any(action not in ALLOWED_FAULT_ACTIONS for action in actions.values()):
            raise ValueError("fault action is not allow-listed")
        object.__setattr__(self, "actions", MappingProxyType({str(key): str(value) for key, value in actions.items()}))
        if isinstance(self.retry_limit, bool) or int(self.retry_limit) < 0:
            raise ValueError("retry_limit must be non-negative")
        object.__setattr__(self, "retry_limit", int(self.retry_limit))

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, "version": self.version, "actions": dict(self.actions), "retry_limit": self.retry_limit}


@dataclass(frozen=True, slots=True)
class ResearchCharter(_Fingerprint):
    charter_id: str
    research_question: str
    hypothesis_scope: str
    dataset_reference: str
    data_split: Mapping[str, Any]
    evaluation_metrics: tuple[str, ...]
    hard_constraints: Mapping[str, Any]
    allowed_primitives: tuple[str, ...]
    max_experiments: int = 20
    iteration_budget: int = 20
    paper_only: bool = True
    test_accessible: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "charter_id", _id(self.charter_id, "charter_id"))
        for field_name in ("research_question", "hypothesis_scope", "dataset_reference"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        object.__setattr__(self, "data_split", _freeze(self.data_split, "data_split"))
        object.__setattr__(self, "hard_constraints", _freeze(self.hard_constraints, "hard_constraints"))
        object.__setattr__(self, "evaluation_metrics", _tuple_text(self.evaluation_metrics, "evaluation metric"))
        object.__setattr__(self, "allowed_primitives", _tuple_text(self.allowed_primitives, "allowed primitive"))
        for field_name in ("max_experiments", "iteration_budget"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or int(value) < 1:
                raise ValueError(f"{field_name} must be a positive integer")
            object.__setattr__(self, field_name, int(value))
        if self.paper_only is not True:
            raise ValueError("paper_only must remain true")

    def assert_test_access(self) -> None:
        if not self.test_accessible:
            raise ValueError("test/OOS data is frozen until explicit test evaluation")

    def freeze_test(self) -> ResearchCharter:
        return replace(self, test_accessible=True)

    def to_dict(self) -> dict[str, Any]:
        return _safe({"charter_id": self.charter_id, "research_question": self.research_question, "hypothesis_scope": self.hypothesis_scope, "dataset_reference": self.dataset_reference, "data_split": self.data_split, "evaluation_metrics": self.evaluation_metrics, "hard_constraints": self.hard_constraints, "allowed_primitives": self.allowed_primitives, "max_experiments": self.max_experiments, "iteration_budget": self.iteration_budget, "paper_only": self.paper_only, "test_accessible": self.test_accessible})


@dataclass(frozen=True, slots=True)
class PolicyProposal(_Fingerprint):
    proposal_id: str
    provider: str
    model: str
    input_context_fingerprint: str
    target_component: str
    allowed_parameter_diff: Mapping[str, Any]
    reasoning_summary: str
    candidate_range: Mapping[str, Any] = field(default_factory=dict)
    required_experiments: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "proposal_id", _id(self.proposal_id, "proposal_id"))
        for field_name in ("provider", "model", "target_component", "reasoning_summary", "input_context_fingerprint"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        diff = _freeze(self.allowed_parameter_diff, "allowed_parameter_diff")
        for key in diff:
            if _EXECUTABLE.search(str(key)) or _EXECUTABLE.search(str(diff[key])):
                raise ValueError("proposal diff contains executable or side-effecting content")
        object.__setattr__(self, "allowed_parameter_diff", diff)
        object.__setattr__(self, "candidate_range", _freeze(self.candidate_range, "candidate_range"))
        object.__setattr__(self, "required_experiments", _tuple_text(self.required_experiments, "required experiment"))
        object.__setattr__(self, "warnings", _tuple_text(self.warnings, "warning"))

    def to_dict(self) -> dict[str, Any]:
        return _safe({"proposal_id": self.proposal_id, "provider": self.provider, "model": self.model, "input_context_fingerprint": self.input_context_fingerprint, "target_component": self.target_component, "allowed_parameter_diff": self.allowed_parameter_diff, "reasoning_summary": self.reasoning_summary, "candidate_range": self.candidate_range, "required_experiments": self.required_experiments, "warnings": self.warnings})


@dataclass(frozen=True, slots=True)
class ParameterChangeExplanation(_Fingerprint):
    explanation_id: str
    strategy_id: str
    parameter_changes: Mapping[str, Mapping[str, Any]]
    intent: str
    formula_before: str
    formula_after: str
    derivation: tuple[str, ...]
    code_trace: tuple[str, ...]
    finance_interpretation: str
    expected_effects: tuple[str, ...]
    paired_metrics: Mapping[str, Any]
    attribution: Mapping[str, Any]
    oos_status: str
    stress_status: str
    stability_status: str
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    next_experiment: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "explanation_id", _id(self.explanation_id, "explanation_id"))
        object.__setattr__(self, "strategy_id", _id(self.strategy_id, "strategy_id"))
        object.__setattr__(self, "parameter_changes", _freeze(self.parameter_changes, "parameter_changes"))
        for field_name in ("intent", "formula_before", "formula_after", "finance_interpretation", "oos_status", "stress_status", "stability_status", "next_experiment"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        for field_name in ("derivation", "code_trace", "expected_effects", "assumptions", "limitations"):
            object.__setattr__(self, field_name, _tuple_text(getattr(self, field_name), field_name))
        object.__setattr__(self, "paired_metrics", _freeze(self.paired_metrics, "paired_metrics"))
        object.__setattr__(self, "attribution", _freeze(self.attribution, "attribution"))

    @property
    def attribution_status(self) -> str:
        if len(self.parameter_changes) > 1:
            return "ATTRIBUTION_CONFOUNDED"
        return str(self.attribution.get("status", "ATTRIBUTION_AVAILABLE"))

    def to_dict(self) -> dict[str, Any]:
        return _safe({"explanation_id": self.explanation_id, "strategy_id": self.strategy_id, "parameter_changes": self.parameter_changes, "intent": self.intent, "formula_before": self.formula_before, "formula_after": self.formula_after, "derivation": self.derivation, "code_trace": self.code_trace, "finance_interpretation": self.finance_interpretation, "expected_effects": self.expected_effects, "paired_metrics": self.paired_metrics, "attribution": {**dict(self.attribution), "status": self.attribution_status}, "oos_status": self.oos_status, "stress_status": self.stress_status, "stability_status": self.stability_status, "assumptions": self.assumptions, "limitations": self.limitations, "next_experiment": self.next_experiment})


__all__ = [
    "ALLOWED_FAULT_ACTIONS",
    "ALLOWED_RISK_ACTIONS",
    "POSITION_MAPPINGS",
    "RISK_STATES",
    "ExecutionPolicy",
    "FaultPolicy",
    "ParameterChangeExplanation",
    "PolicyProposal",
    "PositionPolicySpec",
    "ResearchCharter",
    "RiskStatePolicy",
]
