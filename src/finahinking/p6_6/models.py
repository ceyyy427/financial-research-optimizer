"""Immutable contracts for the P6.6 strategy research and simulation lab.

The objects in this module are deliberately data-only.  They are suitable for
storage, review, and provenance; no object contains a callable or executable
source.  Execution is provided separately by :mod:`compiler` through the
existing P5 backtest protocol.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_IR_KINDS = frozenset(
    {
        "feature_ref",
        "compare",
        "boolean",
        "rank",
        "selection",
        "target_weight",
        "rebalance",
        "next_period_execution",
    }
)


def _safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_safe(item) for item in value]
    if isinstance(value, MappingProxyType):
        return {str(key): _safe(item) for key, item in value.items()}
    if hasattr(value, "item"):
        try:
            return _safe(value.item())
        except (AttributeError, ValueError):
            pass
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def _identifier(value: Any, field_name: str) -> str:
    value = _text(value, field_name)
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{field_name} is invalid")
    return value


def _finite(value: Any, field_name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    return number


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        value = {}
    if not isinstance(value, Mapping):
        raise TypeError("parameters must be a mapping")
    return MappingProxyType({str(key): _safe(item) for key, item in value.items()})


def _tuple_text(values: tuple[str, ...] | list[str] | None, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(_text(value, field_name) for value in values)


@dataclass(frozen=True)
class FeatureDefinition:
    """A versioned, deterministic description of one feature calculation."""

    feature_id: str
    name: str
    description: str
    category: str
    formula: str
    input_fields: tuple[str, ...] = ()
    source_requirements: tuple[str, ...] = ()
    window: int | None = None
    lag: int = 0
    normalization: str = "none"
    missing_policy: str = "propagate"
    availability_rule: str = "available_at <= signal_time"
    cross_sectional_scope: str = "asset"
    parameters: Mapping[str, Any] = field(default_factory=dict)
    version: str = "v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "feature_id", _identifier(self.feature_id, "feature_id"))
        for field_name in ("name", "description", "category", "formula", "normalization", "missing_policy", "availability_rule", "cross_sectional_scope", "version"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        object.__setattr__(self, "input_fields", _tuple_text(self.input_fields, "input field"))
        object.__setattr__(self, "source_requirements", _tuple_text(self.source_requirements, "source requirement"))
        if self.window is not None and (isinstance(self.window, bool) or int(self.window) < 1):
            raise ValueError("window must be a positive integer when supplied")
        if self.window is not None:
            object.__setattr__(self, "window", int(self.window))
        if isinstance(self.lag, bool) or int(self.lag) < 0:
            raise ValueError("lag must be a non-negative integer")
        object.__setattr__(self, "lag", int(self.lag))
        if "future" in self.availability_rule.lower() or "lookahead" in self.availability_rule.lower():
            raise ValueError("availability_rule cannot permit future information")
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "formula": self.formula,
            "input_fields": list(self.input_fields),
            "source_requirements": list(self.source_requirements),
            "window": self.window,
            "lag": self.lag,
            "normalization": self.normalization,
            "missing_policy": self.missing_policy,
            "availability_rule": self.availability_rule,
            "cross_sectional_scope": self.cross_sectional_scope,
            "parameters": _safe(self.parameters),
            "version": self.version,
        }

    @property
    def fingerprint(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True)
class FeatureVersion:
    """Content-addressed feature version; the definition is never mutated."""

    definition: FeatureDefinition
    version_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.definition, FeatureDefinition):
            raise TypeError("definition must be a FeatureDefinition")
        version_id = self.version_id or self.definition.version
        object.__setattr__(self, "version_id", _identifier(version_id, "version_id"))

    @property
    def feature_id(self) -> str:
        return self.definition.feature_id

    @property
    def version(self) -> str:
        return str(self.version_id)

    @property
    def fingerprint(self) -> str:
        return digest({"definition": self.definition.to_dict(), "version_id": self.version_id})

    def to_dict(self) -> dict[str, Any]:
        return {"definition": self.definition.to_dict(), "version_id": self.version_id, "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class FeatureNode:
    node_id: str
    feature: FeatureVersion
    inputs: tuple[str, ...] = ()
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _identifier(self.node_id, "node_id"))
        if not isinstance(self.feature, FeatureVersion):
            raise TypeError("feature must be a FeatureVersion")
        object.__setattr__(self, "inputs", _tuple_text(self.inputs, "input node"))
        object.__setattr__(self, "explanation", self.explanation.strip() if isinstance(self.explanation, str) else "")

    @property
    def feature_id(self) -> str:
        return self.feature.feature_id

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "feature": self.feature.to_dict(), "inputs": list(self.inputs), "explanation": self.explanation}


@dataclass(frozen=True)
class FeatureGraph:
    nodes: tuple[FeatureNode, ...]
    outputs: tuple[str, ...]

    def __post_init__(self) -> None:
        nodes = tuple(self.nodes)
        outputs = _tuple_text(self.outputs, "output node")
        if not nodes:
            raise ValueError("feature graph requires at least one node")
        node_map = {node.node_id: node for node in nodes}
        if len(node_map) != len(nodes):
            raise ValueError("feature graph contains duplicate node ids")
        if not outputs or any(output not in node_map for output in outputs):
            raise ValueError("feature graph outputs must reference registered nodes")
        for node in nodes:
            if any(input_id not in node_map for input_id in node.inputs):
                raise ValueError(f"feature graph input is missing for {node.node_id}")
        self._validate_acyclic(node_map)
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "outputs", outputs)

    @staticmethod
    def _validate_acyclic(node_map: Mapping[str, FeatureNode]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visiting:
                raise ValueError("feature graph contains a cycle")
            if node_id in visited:
                return
            visiting.add(node_id)
            for input_id in node_map[node_id].inputs:
                visit(input_id)
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in node_map:
            visit(node_id)

    @property
    def fingerprint(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": [node.to_dict() for node in self.nodes], "outputs": list(self.outputs), "fingerprint": digest({"nodes": [node.to_dict() for node in self.nodes], "outputs": list(self.outputs)})}

    @property
    def node_map(self) -> dict[str, FeatureNode]:
        return {node.node_id: node for node in self.nodes}


@dataclass(frozen=True)
class StrategySpec:
    """Reviewed meaning of a strategy idea, with all material assumptions."""

    strategy_id: str
    version: str
    name: str
    original_idea: str
    research_question: str
    hypothesis: str
    universe: str
    dataset_reference: str
    feature_versions: tuple[FeatureVersion, ...]
    feature_graph_fingerprint: str
    signal_rule: str
    filter_rule: str
    ranking_rule: str
    selection_rule: str
    entry_rule: str
    exit_rule: str
    position_sizing: str
    portfolio_construction: str
    rebalance_frequency: str
    execution_timing: str
    risk_constraints: tuple[str, ...] = ()
    cost_model: Mapping[str, Any] = field(default_factory=dict)
    benchmark: str = "buy_and_hold"
    validation_design: Mapping[str, Any] = field(default_factory=dict)
    parameters: Mapping[str, Any] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()
    reviewed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "strategy_id", _identifier(self.strategy_id, "strategy_id"))
        object.__setattr__(self, "version", _identifier(self.version, "version"))
        for field_name in ("name", "original_idea", "research_question", "hypothesis", "universe", "dataset_reference", "feature_graph_fingerprint", "signal_rule", "filter_rule", "ranking_rule", "selection_rule", "entry_rule", "exit_rule", "position_sizing", "portfolio_construction", "rebalance_frequency", "execution_timing", "benchmark"):
            object.__setattr__(self, field_name, _text(getattr(self, field_name), field_name))
        if not self.feature_versions or not all(isinstance(item, FeatureVersion) for item in self.feature_versions):
            raise ValueError("feature_versions must contain FeatureVersion objects")
        object.__setattr__(self, "feature_versions", tuple(self.feature_versions))
        object.__setattr__(self, "risk_constraints", _tuple_text(self.risk_constraints, "risk constraint"))
        object.__setattr__(self, "limitations", _tuple_text(self.limitations, "limitation"))
        object.__setattr__(self, "cost_model", _freeze_mapping(self.cost_model))
        object.__setattr__(self, "validation_design", _freeze_mapping(self.validation_design))
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))
        if not isinstance(self.reviewed, bool):
            raise TypeError("reviewed must be boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "version": self.version,
            "name": self.name,
            "original_idea": self.original_idea,
            "research_question": self.research_question,
            "hypothesis": self.hypothesis,
            "universe": self.universe,
            "dataset_reference": self.dataset_reference,
            "feature_versions": [item.to_dict() for item in self.feature_versions],
            "feature_graph_fingerprint": self.feature_graph_fingerprint,
            "signal_rule": self.signal_rule,
            "filter_rule": self.filter_rule,
            "ranking_rule": self.ranking_rule,
            "selection_rule": self.selection_rule,
            "entry_rule": self.entry_rule,
            "exit_rule": self.exit_rule,
            "position_sizing": self.position_sizing,
            "portfolio_construction": self.portfolio_construction,
            "rebalance_frequency": self.rebalance_frequency,
            "execution_timing": self.execution_timing,
            "risk_constraints": list(self.risk_constraints),
            "cost_model": _safe(self.cost_model),
            "benchmark": self.benchmark,
            "validation_design": _safe(self.validation_design),
            "parameters": _safe(self.parameters),
            "limitations": list(self.limitations),
            "reviewed": self.reviewed,
        }

    @property
    def fingerprint(self) -> str:
        return digest(self.to_dict())


@dataclass(frozen=True)
class StrategyVersion:
    spec: StrategySpec

    def __post_init__(self) -> None:
        if not isinstance(self.spec, StrategySpec):
            raise TypeError("spec must be a StrategySpec")
        if not self.spec.reviewed:
            raise ValueError("StrategyVersion requires a reviewed StrategySpec")

    @property
    def strategy_id(self) -> str:
        return self.spec.strategy_id

    @property
    def version(self) -> str:
        return self.spec.version

    @property
    def fingerprint(self) -> str:
        return digest({"spec": self.spec.to_dict()})

    def to_dict(self) -> dict[str, Any]:
        return {"spec": self.spec.to_dict(), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class StrategyReview:
    spec: StrategySpec
    assumptions: tuple[str, ...]
    warnings: tuple[str, ...]
    reviewed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.spec, StrategySpec):
            raise TypeError("spec must be a StrategySpec")
        object.__setattr__(self, "assumptions", _tuple_text(self.assumptions, "assumption"))
        object.__setattr__(self, "warnings", _tuple_text(self.warnings, "warning"))
        if not isinstance(self.reviewed, bool):
            raise TypeError("reviewed must be boolean")

    def accept(self) -> StrategyReview:
        accepted = StrategySpec(**{**self.spec.to_dict(), "feature_versions": self.spec.feature_versions, "cost_model": self.spec.cost_model, "validation_design": self.spec.validation_design, "parameters": self.spec.parameters, "reviewed": True})
        return StrategyReview(accepted, self.assumptions, self.warnings, True)

    @property
    def fingerprint(self) -> str:
        return digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
            "reviewed": self.reviewed,
            "fingerprint": digest({"spec": self.spec.to_dict(), "assumptions": list(self.assumptions), "warnings": list(self.warnings), "reviewed": self.reviewed}),
        }


@dataclass(frozen=True)
class StrategyIRNode:
    node_id: str
    kind: str
    inputs: tuple[str, ...] = ()
    feature_id: str | None = None
    parameters: Mapping[str, Any] = field(default_factory=dict)
    explanation: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_id", _identifier(self.node_id, "node_id"))
        object.__setattr__(self, "kind", _text(self.kind, "kind"))
        if self.kind not in _IR_KINDS:
            raise ValueError(f"unsupported strategy IR node kind: {self.kind}")
        object.__setattr__(self, "inputs", _tuple_text(self.inputs, "input node"))
        if self.feature_id is not None:
            object.__setattr__(self, "feature_id", _identifier(self.feature_id, "feature_id"))
        object.__setattr__(self, "parameters", _freeze_mapping(self.parameters))
        object.__setattr__(self, "explanation", self.explanation.strip() if isinstance(self.explanation, str) else "")

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "kind": self.kind, "inputs": list(self.inputs), "feature_id": self.feature_id, "parameters": _safe(self.parameters), "explanation": self.explanation}


@dataclass(frozen=True)
class StrategyIR:
    strategy_version: StrategyVersion
    feature_graph_fingerprint: str
    nodes: tuple[StrategyIRNode, ...]
    compiler_version: str = "p6.6.compiler.1"

    def __post_init__(self) -> None:
        if not isinstance(self.strategy_version, StrategyVersion):
            raise TypeError("strategy_version must be a StrategyVersion")
        object.__setattr__(self, "feature_graph_fingerprint", _text(self.feature_graph_fingerprint, "feature_graph_fingerprint"))
        object.__setattr__(self, "compiler_version", _identifier(self.compiler_version, "compiler_version"))
        nodes = tuple(self.nodes)
        node_map = {node.node_id: node for node in nodes}
        if len(nodes) != len(node_map) or not nodes:
            raise ValueError("strategy IR requires unique nodes")
        for node in nodes:
            if any(input_id not in node_map for input_id in node.inputs):
                raise ValueError(f"strategy IR input is missing for {node.node_id}")
            if node.kind == "feature_ref" and not node.feature_id:
                raise ValueError("feature_ref nodes require feature_id")
        object.__setattr__(self, "nodes", nodes)

    @property
    def fingerprint(self) -> str:
        return digest(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        payload = {"strategy_version": self.strategy_version.to_dict(), "feature_graph_fingerprint": self.feature_graph_fingerprint, "nodes": [node.to_dict() for node in self.nodes], "compiler_version": self.compiler_version}
        if include_fingerprint:
            payload["fingerprint"] = self.fingerprint
        return payload


__all__ = [
    "FeatureDefinition",
    "FeatureGraph",
    "FeatureNode",
    "FeatureVersion",
    "StrategyIR",
    "StrategyIRNode",
    "StrategyReview",
    "StrategySpec",
    "StrategyVersion",
    "canonical_json",
    "digest",
]
