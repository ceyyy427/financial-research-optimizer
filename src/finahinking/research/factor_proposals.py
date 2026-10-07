"""Governed, paper-only factor proposal catalog.

Natural language selects a versioned family of fixed expressions; it never
becomes executable Python or a registry mutation.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from finahinking.factors.dsl import parse_factor_expression

_FIELDS = frozenset({"close", "volume", "return_1d"})
_FAMILIES = frozenset({"mean_reversion", "momentum", "volatility", "liquidity"})
_DIRECTIONS = frozenset({"positive", "negative", "neutral"})
_UNSAFE = re.compile(r"(?:eval|exec|__import__|shell|subprocess|https?://|file://|/|\\|future|lookahead)", re.IGNORECASE)


def _norm(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty")
    return " ".join(value.split()).casefold()


@dataclass(frozen=True, slots=True)
class FactorHypothesis:
    hypothesis_id: str
    text: str
    family: str
    inputs: tuple[str, ...]
    horizon: int
    direction: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "hypothesis_id", _norm(self.hypothesis_id, "hypothesis_id"))
        object.__setattr__(self, "text", _norm(self.text, "text"))
        family = _norm(self.family, "family").replace("-", "_").replace(" ", "_")
        if family not in _FAMILIES:
            raise ValueError(f"unknown factor family: {family}")
        object.__setattr__(self, "family", family)
        fields = tuple(sorted({_norm(item, "inputs") for item in self.inputs}))
        if not fields or any(item not in _FIELDS for item in fields):
            raise ValueError("inputs contain a field outside the data whitelist")
        if family == "liquidity" and "volume" not in fields:
            raise ValueError("liquidity hypotheses require volume")
        if family in {"momentum", "mean_reversion", "volatility"} and not ({"close", "return_1d"} & set(fields)):
            raise ValueError(f"{family} hypotheses require close or return_1d")
        if _UNSAFE.search(self.text):
            raise ValueError("hypothesis contains unsafe or future-looking text")
        object.__setattr__(self, "inputs", fields)
        if isinstance(self.horizon, bool) or not isinstance(self.horizon, int) or not 1 <= self.horizon <= 252:
            raise ValueError("horizon must be an integer between 1 and 252")
        direction = _norm(self.direction, "direction")
        if direction not in _DIRECTIONS:
            raise ValueError("direction is not supported")
        object.__setattr__(self, "direction", direction)


@dataclass(frozen=True, slots=True)
class FactorProposal:
    proposal_id: str
    expression: str
    source_hypothesis: str
    required_fields: tuple[str, ...]
    constraints: Mapping[str, Any]
    paper_only: bool = True


def _templates(hypothesis: FactorHypothesis) -> tuple[str, ...]:
    window = hypothesis.horizon
    windows = tuple(dict.fromkeys((window, min(252, max(1, window * 2)))))
    base = "return_1d" if "return_1d" in hypothesis.inputs else "close"
    expressions: list[str] = []
    for current in windows:
        if hypothesis.family == "momentum":
            expressions.append(f"rank(rolling_mean({base},{current}))")
        elif hypothesis.family == "mean_reversion":
            expressions.append(f"negate(rank(rolling_mean({base},{current})))")
        elif hypothesis.family == "volatility":
            expressions.append(f"negate(rank(rolling_std({base},{current})))")
        elif hypothesis.family == "liquidity" and "volume" in hypothesis.inputs:
            expressions.append(f"rank(rolling_mean(volume,{current}))")
    if hypothesis.family == "liquidity" and "volume" not in hypothesis.inputs:
        raise ValueError("liquidity hypotheses require volume")
    return tuple(expressions)


class FactorProposalCatalog:
    def propose(self, hypothesis: FactorHypothesis, limit: int = 5) -> tuple[FactorProposal, ...]:
        if not isinstance(hypothesis, FactorHypothesis):
            raise TypeError("hypothesis must be a FactorHypothesis")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 32:
            raise ValueError("limit must be between 1 and 32")
        proposals: list[FactorProposal] = []
        for expression in _templates(hypothesis):
            parsed = parse_factor_expression(expression, hypothesis.inputs)
            payload = f"{hypothesis.hypothesis_id}|{parsed.expression}|{','.join(parsed.fields)}".encode()
            digest = hashlib.sha256(payload).hexdigest()[:12]
            proposals.append(FactorProposal(
                proposal_id=f"factor-proposal-{digest}",
                expression=parsed.expression,
                source_hypothesis=hypothesis.hypothesis_id,
                required_fields=parsed.fields,
                constraints={"max_window": 252, "point_in_time": True, "paper_only": True},
            ))
        proposals.sort(key=lambda item: item.proposal_id)
        return tuple(proposals[:limit])


def validate_factor_proposal(proposal: FactorProposal) -> None:
    if not isinstance(proposal, FactorProposal):
        raise TypeError("proposal must be a FactorProposal")
    if proposal.paper_only is not True:
        raise ValueError("factor proposals must be paper-only")
    if _UNSAFE.search(proposal.expression) or _UNSAFE.search(proposal.source_hypothesis):
        raise ValueError("proposal contains unsafe or future-looking content")
    fields = tuple(str(item).strip() for item in proposal.required_fields)
    if not fields or any(item not in _FIELDS for item in fields):
        raise ValueError("proposal references a field outside the data whitelist")
    parsed = parse_factor_expression(proposal.expression, fields)
    if parsed.fields != tuple(sorted(set(fields))):
        raise ValueError("required_fields must match expression dependencies")
    constraints = dict(proposal.constraints)
    if constraints != {"max_window": 252, "point_in_time": True, "paper_only": True}:
        raise ValueError("proposal constraints are not the governed catalog constraints")
    payload = f"{proposal.source_hypothesis}|{parsed.expression}|{','.join(parsed.fields)}".encode()
    expected = f"factor-proposal-{hashlib.sha256(payload).hexdigest()[:12]}"
    if proposal.proposal_id != expected:
        raise ValueError("proposal provenance digest does not match its contents")
