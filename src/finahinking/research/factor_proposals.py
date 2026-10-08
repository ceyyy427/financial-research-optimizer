"""Governed, paper-only factor proposal catalog.

Natural language selects a versioned family of fixed expressions; it never
becomes executable Python or a registry mutation.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from finahinking.factors.dsl import parse_factor_expression

_FIELDS = frozenset({"close", "volume", "return_1d"})
_FAMILIES = frozenset({"mean_reversion", "momentum", "volatility", "liquidity"})
_DIRECTIONS = frozenset({"positive", "negative", "neutral"})
_UNSAFE = re.compile(r"(?:eval|exec|__import__|shell|subprocess|https?://|file://|/|\\|future|lookahead)", re.IGNORECASE)
_TEMPLATE_FIELDS = frozenset({"window", "field"})


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
    template_name: str = ""
    template_version: str = ""

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
        if self.template_name:
            object.__setattr__(self, "template_name", _norm(self.template_name, "template_name"))
        if self.template_version:
            object.__setattr__(self, "template_version", _norm(self.template_version, "template_version"))


@dataclass(frozen=True, slots=True)
class FactorTemplate:
    name: str
    family: str
    expression_template: str
    required_fields: tuple[str, ...]
    version: str


class FactorTemplateRegistry:
    """Registry for fixed, versioned factor DSL expressions.

    Template rendering only substitutes a bounded window and allow-listed field;
    the resulting expression is always parsed by the factor DSL parser.
    """

    def __init__(self, templates: Mapping[str, FactorTemplate] | None = None) -> None:
        self._templates: dict[str, FactorTemplate] = {}
        for template in (templates or _default_templates()):
            self.register(template.name, template.family, template.expression_template, template.required_fields, template.version)

    def register(self, name: str, family: str, expression_template: str, required_fields: Sequence[str], version: str) -> FactorTemplate:
        normalized_name = _norm(name, "name").replace(" ", "_").replace("-", "_")
        normalized_family = _norm(family, "family").replace(" ", "_").replace("-", "_")
        if normalized_family not in _FAMILIES:
            raise ValueError(f"unknown factor family: {normalized_family}")
        if not isinstance(expression_template, str) or not expression_template.strip() or len(expression_template) > 512:
            raise ValueError("expression_template must be a bounded non-empty string")
        if _UNSAFE.search(expression_template):
            raise ValueError("template contains unsafe or future-looking content")
        names = tuple(sorted({_norm(item, "required_fields") for item in required_fields}))
        if not names or any(item not in _FIELDS for item in names):
            raise ValueError("required_fields contain a field outside the data whitelist")
        if not isinstance(version, str) or not version.strip():
            raise ValueError("version must be non-empty")
        placeholders = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", expression_template))
        if placeholders - _TEMPLATE_FIELDS:
            raise ValueError("template contains an unsupported placeholder")
        if normalized_name in self._templates:
            raise ValueError(f"factor template {normalized_name} is already registered")
        template = FactorTemplate(normalized_name, normalized_family, expression_template.strip(), names, version.strip())
        self._templates[normalized_name] = template
        return template

    def get(self, name: str) -> FactorTemplate:
        key = _norm(name, "name").replace(" ", "_").replace("-", "_")
        try:
            return self._templates[key]
        except KeyError as exc:
            raise ValueError(f"unknown factor template: {key}") from exc

    def resolve(self, text: str, config: Mapping[str, Any]) -> FactorHypothesis:
        if not isinstance(text, str) or not text.strip() or _UNSAFE.search(text):
            raise ValueError("unknown or unsafe factor language")
        config = dict(config or {})
        lowered = " ".join(text.casefold().split())
        requested = config.get("template") or config.get("template_name")
        template = self.get(str(requested)) if requested is not None else None
        if template is None:
            # Exact template names and a small, explicit family vocabulary only.
            for candidate in sorted(self._templates.values(), key=lambda item: len(item.name), reverse=True):
                if re.search(rf"\b{re.escape(candidate.name.replace('_', ' '))}\b", lowered):
                    template = candidate
                    break
        if template is None:
            family = config.get("family")
            aliases = (("mean_reversion", ("mean reversion", "reversion", "reversal")), ("momentum", ("momentum", "trend")), ("volatility", ("volatility", "vol")), ("liquidity", ("liquidity", "volume")))
            if family is None:
                family = next((name for name, words in aliases if any(word in lowered for word in words)), None)
            if family is None:
                raise ValueError("unknown factor language")
            matching = [item for item in self._templates.values() if item.family == str(family).casefold().replace(" ", "_")]
            if not matching:
                raise ValueError("unknown factor template family")
            template = sorted(matching, key=lambda item: item.name)[0]
        raw_window = config.get("horizon", config.get("window", 20))
        if isinstance(raw_window, bool) or not isinstance(raw_window, int) or not 1 <= raw_window <= 252:
            raise ValueError("window must be an integer between 1 and 252")
        raw_fields = config.get("inputs", config.get("required_fields", template.required_fields))
        fields = tuple(sorted({_norm(item, "inputs") for item in raw_fields}))
        if not fields or any(item not in _FIELDS for item in fields) or not set(template.required_fields).issubset(fields):
            raise ValueError("inputs contain a field outside the data whitelist or omit template fields")
        base_field = "return_1d" if "return_1d" in fields and "return_1d" in template.required_fields else template.required_fields[0]
        expression = template.expression_template.format(window=raw_window, field=base_field)
        parse_factor_expression(expression, fields)
        family = template.family
        direction = config.get("direction", "positive")
        return FactorHypothesis(
            str(config.get("hypothesis_id", f"hypothesis-{hashlib.sha256(text.encode()).hexdigest()[:12]}")), text,
            family, fields, raw_window, direction, template.name, template.version,
        )

    def list(self) -> tuple[FactorTemplate, ...]:
        return tuple(self._templates[key] for key in sorted(self._templates))


def _default_templates() -> tuple[FactorTemplate, ...]:
    return (
        FactorTemplate("mean_reversion", "mean_reversion", "negate(rank(rolling_mean({field},{window})))", ("close",), "1.0.0"),
        FactorTemplate("momentum", "momentum", "rank(rolling_mean({field},{window}))", ("return_1d",), "1.0.0"),
        FactorTemplate("volatility", "volatility", "negate(rank(rolling_std({field},{window})))", ("return_1d",), "1.0.0"),
        FactorTemplate("liquidity", "liquidity", "rank(rolling_mean(volume,{window}))", ("volume",), "1.0.0"),
        FactorTemplate("short_term_reversal", "mean_reversion", "negate(rank(rolling_mean({field},{window})))", ("return_1d",), "1.0.0"),
        FactorTemplate("volume_trend", "liquidity", "rank(rolling_mean(volume,{window}))", ("volume",), "1.0.0"),
    )


@dataclass(frozen=True, slots=True)
class FactorProposal:
    proposal_id: str
    expression: str
    source_hypothesis: str
    required_fields: tuple[str, ...]
    constraints: Mapping[str, Any]
    paper_only: bool = True


def _templates(hypothesis: FactorHypothesis) -> tuple[str, ...]:
    if hypothesis.template_name:
        template = FactorTemplateRegistry().get(hypothesis.template_name)
        field = "return_1d" if "return_1d" in hypothesis.inputs and "return_1d" in template.required_fields else template.required_fields[0]
        return tuple(template.expression_template.format(field=field, window=current) for current in tuple(dict.fromkeys((hypothesis.horizon, min(252, max(1, hypothesis.horizon * 2))))) )
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
