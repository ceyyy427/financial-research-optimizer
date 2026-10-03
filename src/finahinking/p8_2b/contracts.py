"""Immutable, JSON-safe contracts for the P8.2B learning layer."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .math import MathExpression


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def _id(value: str, label: str) -> str:
    value = _text(value, label)
    if any(char.isspace() for char in value) or len(value) > 128:
        raise ValueError(f"{label} must be a bounded identifier")
    return value


def _unique(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    values = tuple(_text(value, label) for value in values)
    if len(values) != len(set(values)):
        raise ValueError(f"{label} values must be unique")
    return values


def _json(value: Any) -> Any:
    json.dumps(value, sort_keys=True, allow_nan=False)
    return value


class ProvenanceKind(str, Enum):
    SOURCE_BACKED = "SOURCE_BACKED"
    DERIVED_FROM_MATHEMATICS = "DERIVED_FROM_MATHEMATICS"
    FINATHINK_EXPLANATION = "FINATHINK_EXPLANATION"
    GENERATED_EXAMPLE = "GENERATED_EXAMPLE"
    CURRENT_RESEARCH_RESULT = "CURRENT_RESEARCH_RESULT"


@dataclass(frozen=True)
class SymbolDefinition:
    symbol_id: str
    notation: str
    meaning: str
    units: str
    current_value: float | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol_id", _id(self.symbol_id, "symbol_id"))
        object.__setattr__(self, "notation", _text(self.notation, "notation"))
        object.__setattr__(self, "meaning", _text(self.meaning, "meaning"))
        object.__setattr__(self, "units", _text(self.units, "units"))
        if self.current_value is not None and (not isinstance(self.current_value, (int, float)) or self.current_value != self.current_value):
            raise ValueError("current_value must be finite")

    def to_dict(self) -> dict[str, object]:
        return {"symbol_id": self.symbol_id, "notation": self.notation, "meaning": self.meaning, "units": self.units, "current_value": self.current_value}


@dataclass(frozen=True)
class EquationDefinition:
    equation_id: str
    expression: MathExpression
    meaning: str
    symbol_ids: tuple[str, ...] = ()
    number: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "equation_id", _id(self.equation_id, "equation_id"))
        if not isinstance(self.expression, MathExpression):
            object.__setattr__(self, "expression", MathExpression.from_node(self.expression.get("ast", self.expression)))
        object.__setattr__(self, "meaning", _text(self.meaning, "meaning"))
        object.__setattr__(self, "symbol_ids", _unique(self.symbol_ids, "symbol_id"))
        if self.number is not None:
            object.__setattr__(self, "number", _text(self.number, "number"))

    def to_dict(self) -> dict[str, object]:
        return {"equation_id": self.equation_id, "expression": self.expression.to_dict(), "meaning": self.meaning, "symbol_ids": list(self.symbol_ids), "number": self.number}


@dataclass(frozen=True)
class DerivationStep:
    step_id: str
    previous_equation_id: str | None
    result: MathExpression
    operation: str
    reason: str
    rule_or_theorem: str
    assumptions: tuple[str, ...]
    reference_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _id(self.step_id, "step_id"))
        if self.previous_equation_id is not None:
            object.__setattr__(self, "previous_equation_id", _id(self.previous_equation_id, "previous_equation_id"))
        if not isinstance(self.result, MathExpression):
            object.__setattr__(self, "result", MathExpression.from_node(self.result.get("ast", self.result)))
        for name in ("operation", "reason", "rule_or_theorem"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "assumptions", _unique(self.assumptions, "assumption"))
        object.__setattr__(self, "reference_ids", _unique(self.reference_ids, "reference_id"))

    def to_dict(self) -> dict[str, object]:
        return {"step_id": self.step_id, "previous_equation_id": self.previous_equation_id, "result": self.result.to_dict(), "operation": self.operation, "reason": self.reason, "rule_or_theorem": self.rule_or_theorem, "assumptions": list(self.assumptions), "reference_ids": list(self.reference_ids)}


@dataclass(frozen=True)
class Proof:
    proof_id: str
    statement: str
    strategy: str
    step_ids: tuple[str, ...]
    status: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "proof_id", _id(self.proof_id, "proof_id"))
        for name in ("statement", "strategy", "status"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "step_ids", _unique(self.step_ids, "step_id"))
        if self.status not in {"SYMBOLICALLY_VERIFIED", "HUMAN_REVIEWED", "REFERENCE_DERIVED"}:
            raise ValueError("proof status is invalid")

    def to_dict(self) -> dict[str, object]:
        return {"proof_id": self.proof_id, "statement": self.statement, "strategy": self.strategy, "step_ids": list(self.step_ids), "status": self.status}


@dataclass(frozen=True)
class CodeSegment:
    segment_id: str
    code: str
    line_range: tuple[int, int]
    equation_ids: tuple[str, ...]
    feature_ids: tuple[str, ...]
    data_input: str
    data_output: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "segment_id", _id(self.segment_id, "segment_id"))
        object.__setattr__(self, "code", _text(self.code, "code"))
        if len(self.line_range) != 2 or not all(isinstance(value, int) and value > 0 for value in self.line_range) or self.line_range[0] > self.line_range[1]:
            raise ValueError("line_range is invalid")
        object.__setattr__(self, "equation_ids", _unique(self.equation_ids, "equation_id"))
        object.__setattr__(self, "feature_ids", _unique(self.feature_ids, "feature_id"))
        object.__setattr__(self, "data_input", _text(self.data_input, "data_input"))
        object.__setattr__(self, "data_output", _text(self.data_output, "data_output"))

    def to_dict(self) -> dict[str, object]:
        return {"segment_id": self.segment_id, "code": self.code, "line_range": list(self.line_range), "equation_ids": list(self.equation_ids), "feature_ids": list(self.feature_ids), "data_input": self.data_input, "data_output": self.data_output}


@dataclass(frozen=True)
class DataTrace:
    trace_id: str
    steps: tuple[str, ...]
    sample_values: tuple[dict[str, object], ...]
    source_state: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "trace_id", _id(self.trace_id, "trace_id"))
        object.__setattr__(self, "steps", _unique(self.steps, "step"))
        object.__setattr__(self, "sample_values", tuple(_json(dict(value)) for value in self.sample_values))
        object.__setattr__(self, "source_state", _text(self.source_state, "source_state"))

    def to_dict(self) -> dict[str, object]:
        return {"trace_id": self.trace_id, "steps": list(self.steps), "sample_values": list(self.sample_values), "source_state": self.source_state}


@dataclass(frozen=True)
class KnowledgeUnit:
    unit_id: str
    title: str
    domain: str
    level: str
    why_now: str
    background: str
    intuition: str
    symbols: tuple[SymbolDefinition, ...]
    equations: tuple[EquationDefinition | dict[str, object], ...]
    prerequisites: tuple[str, ...]
    code_segments: tuple[CodeSegment, ...]
    references: tuple[str, ...]
    provenance: ProvenanceKind
    assumptions: tuple[str, ...]
    limitations: tuple[str, ...]
    derivations: tuple[DerivationStep, ...] = ()
    proofs: tuple[Proof, ...] = ()
    misconceptions: tuple[dict[str, str], ...] = ()
    exercises: tuple[dict[str, object], ...] = ()
    applications: tuple[str, ...] = ()
    data_trace: DataTrace | None = None
    tags: tuple[str, ...] = ()
    history: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "unit_id", _id(self.unit_id, "unit_id"))
        for name in ("title", "domain", "level", "why_now", "background", "intuition"):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, "history", _text(self.history or self.background, "history"))
        object.__setattr__(self, "symbols", tuple(self.symbols))
        object.__setattr__(self, "equations", tuple(EquationDefinition(**item) if isinstance(item, dict) and "equation_id" in item else item for item in self.equations))
        if not self.equations or not self.code_segments or not self.references:
            raise ValueError("equations, code_segments, and references are required")
        object.__setattr__(self, "prerequisites", _unique(self.prerequisites, "prerequisite"))
        object.__setattr__(self, "references", _unique(self.references, "reference_id"))
        object.__setattr__(self, "assumptions", _unique(self.assumptions, "assumption"))
        object.__setattr__(self, "limitations", _unique(self.limitations, "limitation"))
        object.__setattr__(self, "applications", _unique(self.applications, "application"))
        object.__setattr__(self, "tags", _unique(self.tags, "tag"))
        if not isinstance(self.provenance, ProvenanceKind):
            object.__setattr__(self, "provenance", ProvenanceKind(self.provenance))

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, allow_nan=False).encode()).hexdigest()

    def to_dict(self) -> dict[str, object]:
        return {"unit_id": self.unit_id, "title": self.title, "domain": self.domain, "level": self.level, "why_now": self.why_now, "background": self.background, "history": self.history, "intuition": self.intuition, "symbols": [item.to_dict() for item in self.symbols], "equations": [item.to_dict() for item in self.equations], "prerequisites": list(self.prerequisites), "code_segments": [item.to_dict() for item in self.code_segments], "references": list(self.references), "provenance": self.provenance.value, "assumptions": list(self.assumptions), "limitations": list(self.limitations), "derivations": [item.to_dict() for item in self.derivations], "proofs": [item.to_dict() for item in self.proofs], "misconceptions": list(self.misconceptions), "exercises": list(self.exercises), "applications": list(self.applications), "data_trace": self.data_trace.to_dict() if self.data_trace else None, "tags": list(self.tags)}

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> KnowledgeUnit:
        expressions = []
        for item in payload["equations"]:
            expression = item["expression"]
            expressions.append({**item, "expression": MathExpression.from_node(expression.get("ast", expression))})
        return cls(
            unit_id=payload["unit_id"], title=payload["title"], domain=payload["domain"], level=payload["level"], why_now=payload["why_now"], background=payload["background"], history=payload.get("history", payload["background"]), intuition=payload["intuition"], symbols=tuple(SymbolDefinition(**item) for item in payload["symbols"]), equations=tuple(expressions), prerequisites=tuple(payload["prerequisites"]), code_segments=tuple(CodeSegment(item["segment_id"], item["code"], tuple(item["line_range"]), tuple(item["equation_ids"]), tuple(item["feature_ids"]), item["data_input"], item["data_output"]) for item in payload["code_segments"]), references=tuple(payload["references"]), provenance=payload["provenance"], assumptions=tuple(payload["assumptions"]), limitations=tuple(payload["limitations"]), derivations=(), proofs=(), misconceptions=tuple(payload.get("misconceptions", ())), exercises=tuple(payload.get("exercises", ())), applications=tuple(payload.get("applications", ())), tags=tuple(payload.get("tags", ())))


@dataclass(frozen=True)
class KnowledgeContextBinding:
    knowledge_unit_id: str
    context_type: str
    context_id: str
    why_now: str
    current_values: tuple[dict[str, object], ...]
    evidence_ids: tuple[str, ...]
    feature_id: str | None
    research_run_id: str | None
    context_time: str
    available_at: str
    dataset_fingerprint: str
    source_state: str
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("knowledge_unit_id", "context_type", "context_id", "dataset_fingerprint", "source_state"):
            object.__setattr__(self, name, _id(getattr(self, name), name))
        object.__setattr__(self, "why_now", _text(self.why_now, "why_now"))
        if self.available_at > self.context_time:
            raise ValueError("available_at cannot be after context_time")
        object.__setattr__(self, "current_values", tuple(_json(dict(value)) for value in self.current_values))
        object.__setattr__(self, "evidence_ids", _unique(self.evidence_ids, "evidence_id"))
        object.__setattr__(self, "limitations", _unique(self.limitations, "limitation"))

    def to_dict(self) -> dict[str, object]:
        return {"knowledge_unit_id": self.knowledge_unit_id, "context_type": self.context_type, "context_id": self.context_id, "why_now": self.why_now, "current_values": list(self.current_values), "evidence_ids": list(self.evidence_ids), "feature_id": self.feature_id, "research_run_id": self.research_run_id, "context_time": self.context_time, "available_at": self.available_at, "dataset_fingerprint": self.dataset_fingerprint, "source_state": self.source_state, "limitations": list(self.limitations)}
