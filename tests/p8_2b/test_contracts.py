from __future__ import annotations

import json

import pytest

from finahinking.p8_2b.contracts import (
    CodeSegment,
    KnowledgeContextBinding,
    KnowledgeUnit,
    ProvenanceKind,
    SymbolDefinition,
)
from finahinking.p8_2b.math import MathExpression


def test_math_expression_is_canonical_json_and_knowledge_unit_round_trips() -> None:
    expression = MathExpression.divide(MathExpression.symbol("x"), MathExpression.number(2))
    unit = KnowledgeUnit(
        unit_id="returns",
        title="Returns",
        domain="finance",
        level="FOUNDATION",
        why_now="The selected price series needs a comparable change measure.",
        background="Returns compare a later value with an earlier value.",
        intuition="A return is the change relative to the starting value.",
        symbols=(SymbolDefinition("x", "x", "starting value", "price", None),),
        equations=(
            {
                "equation_id": "simple-return",
                "expression": expression.to_dict(),
                "meaning": "relative change",
            },
        ),
        prerequisites=(),
        code_segments=(CodeSegment("returns-code", "return = (p1 - p0) / p0", (1, 1), ("simple-return",), (), "price inputs", "return output"),),
        references=("ref-returns",),
        provenance=ProvenanceKind.FINATHINK_EXPLANATION,
        assumptions=("p0 is non-zero",),
        limitations=("Historical returns do not guarantee future returns.",),
    )
    payload = unit.to_dict()
    assert json.loads(expression.ast)["type"] == "binary"
    assert KnowledgeUnit.from_dict(payload) == unit
    assert unit.fingerprint == KnowledgeUnit.from_dict(payload).fingerprint


def test_context_binding_rejects_future_availability_and_missing_why_now() -> None:
    with pytest.raises(ValueError, match="why_now"):
        KnowledgeContextBinding("returns", "research_point", "p1", "", (), (), None, None, "2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", "fp", "AVAILABLE")
    with pytest.raises(ValueError, match="available_at"):
        KnowledgeContextBinding("returns", "research_point", "p1", "why", (), (), None, None, "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z", "fp", "AVAILABLE")
