from __future__ import annotations

import math

import pytest

from finahinking.p8_2b.math import (
    MathExpression,
    equivalent,
    evaluate,
    render_latex,
    render_mathml,
    substitute,
    symbolic_equivalence,
)


def test_ast_renders_latex_mathml_and_supports_finite_substitution() -> None:
    expression = MathExpression.divide(
        MathExpression.subtract(MathExpression.symbol("r"), MathExpression.symbol("rf")),
        MathExpression.symbol("sigma"),
    )
    assert render_latex(expression) == r"\frac{r - rf}{sigma}"
    assert "<math" in render_mathml(expression)
    substituted = substitute(expression, {"r": 0.12, "rf": 0.02, "sigma": 0.2})
    assert evaluate(substituted) == pytest.approx(0.5)
    assert math.isfinite(evaluate(substituted))


def test_equivalence_normalizes_commutative_addition_and_rejects_nonfinite_values() -> None:
    assert equivalent(MathExpression.add(MathExpression.symbol("a"), MathExpression.symbol("b")), MathExpression.add(MathExpression.symbol("b"), MathExpression.symbol("a")))
    with pytest.raises(ValueError, match="finite"):
        MathExpression.number(float("nan"))
    with pytest.raises(ValueError, match="unknown symbol"):
        substitute(MathExpression.symbol("x"), {})


def test_symbolic_adapter_is_explicit_about_verification_capability() -> None:
    result, status = symbolic_equivalence(MathExpression.add(MathExpression.symbol("x"), MathExpression.symbol("y")), MathExpression.add(MathExpression.symbol("y"), MathExpression.symbol("x")))
    assert result is True
    assert status in {"SYMBOLICALLY_VERIFIED", "UNAVAILABLE_AST_NORMALIZATION", "AST_FALLBACK"}
