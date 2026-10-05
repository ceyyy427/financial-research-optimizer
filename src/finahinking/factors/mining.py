"""Bounded, deterministic factor candidate templates."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .dsl import parse_factor_expression


@dataclass(frozen=True, slots=True)
class FactorCandidate:
    candidate_id: str
    expression: str
    hypothesis: str
    source: str
    metadata: Mapping[str, Any]

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.expression.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "expression": self.expression,
            "hypothesis": self.hypothesis,
            "source": self.source,
            "metadata": dict(self.metadata),
            "fingerprint": self.fingerprint,
        }


def _templates(hypothesis: str, fields: set[str]) -> list[tuple[str, str]]:
    has_close = "close" in fields
    has_volume = "volume" in fields
    has_return = "return_1d" in fields
    base = "return_1d" if has_return else "close"
    templates: list[tuple[str, str]] = []
    if has_close or has_return:
        templates.extend(
            [
                (f"rank(rolling_mean({base},20))", "trend persistence"),
                (f"rank(rolling_mean({base},60))", "slower trend persistence"),
                (f"negate(rank(rolling_mean({base},5)))", "short-horizon mean reversion"),
                (f"negate(rank(rolling_std({base},20)))", "low-volatility tilt"),
            ]
        )
    if has_volume:
        templates.extend(
            [
                ("rank(rolling_mean(volume,20))", "liquidity participation"),
                ("negate(rank(rolling_std(volume,20)))", "stable volume regime"),
            ]
        )
    if has_close and has_volume:
        templates.append(("combine(rank(close),negate(rank(volume)))", "price-volume contrast"))
    return templates


def generate_candidates(
    hypothesis: str,
    *,
    field_catalog: Sequence[str],
    operator_catalog: Sequence[str] = (),
    max_candidates: int = 8,
    source: str = "offline-template",
) -> tuple[FactorCandidate, ...]:
    if not isinstance(hypothesis, str) or not hypothesis.strip():
        raise ValueError("hypothesis must be non-empty")
    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int) or not 1 <= max_candidates <= 32:
        raise ValueError("max_candidates must be between 1 and 32")
    fields = {str(item).strip() for item in field_catalog if str(item).strip()}
    if not fields:
        raise ValueError("field_catalog must not be empty")
    templates = _templates(hypothesis.strip(), fields)
    candidates: list[FactorCandidate] = []
    allowed = tuple(operator_catalog) if operator_catalog else ()
    for expression, rationale in templates:
        parsed = parse_factor_expression(expression, fields, allowed or None)
        digest = hashlib.sha256(parsed.expression.encode("utf-8")).hexdigest()[:12]
        candidates.append(
            FactorCandidate(
                candidate_id=f"factor-candidate-{digest}",
                expression=parsed.expression,
                hypothesis=f"{hypothesis.strip()}: {rationale}",
                source=source,
                metadata={"fields": parsed.fields, "operators": parsed.operators},
            )
        )
    candidates.sort(key=lambda item: item.candidate_id)
    return tuple(candidates[:max_candidates])

