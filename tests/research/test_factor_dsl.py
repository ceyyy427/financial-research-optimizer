from __future__ import annotations

import pandas as pd
import pytest

from finahinking.factors.dsl import evaluate_expression, parse_factor_expression
from finahinking.factors.mining import generate_candidates


def _frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=8, freq="D", tz="UTC")
    return pd.DataFrame(
        {"close": [100, 101, 99, 102, 104, 103, 106, 108], "volume": [10, 12, 9, 15, 14, 16, 18, 17]},
        index=index,
    )


def test_parser_normalizes_expression_and_collects_dependencies() -> None:
    first = parse_factor_expression(" rank( rolling_mean( return(close, 1), 3 ) ) ", {"close"})
    second = parse_factor_expression("rank(rolling_mean(return(close,1),3))", {"close"})

    assert first.expression == "rank(rolling_mean(return(close,1),3))"
    assert first.fields == ("close",)
    assert first.operators == ("rank", "return", "rolling_mean")
    assert first.fingerprint == second.fingerprint


@pytest.mark.parametrize(
    "expression",
    ["__import__('os')", "eval(close)", "close + volume", "unknown(close, 3)", "rolling_mean(close, 1001)", "close('/etc/passwd')"],
)
def test_parser_rejects_unregistered_or_executable_expression(expression: str) -> None:
    with pytest.raises(ValueError):
        parse_factor_expression(expression, {"close", "volume"})


def test_evaluator_is_point_in_time_bounded_and_deterministic() -> None:
    frame = _frame()
    as_of = frame.index[5]
    result = evaluate_expression("rank(rolling_mean(return(close,1),3))", frame, as_of=as_of)

    assert result.index.max() == as_of
    assert result.index.is_monotonic_increasing
    assert result.equals(evaluate_expression("rank(rolling_mean(return(close,1),3))", frame, as_of=as_of))

    with pytest.raises(ValueError, match="availability"):
        evaluate_expression("close", frame, as_of=as_of, available_at={"close": as_of + pd.Timedelta(days=1)})


def test_candidate_generation_is_bounded_and_sorted() -> None:
    kwargs = {"field_catalog": ("close", "volume"), "operator_catalog": (), "max_candidates": 4}
    first = generate_candidates("mean reversion with volume", **kwargs)
    second = generate_candidates("mean reversion with volume", **kwargs)

    assert len(first) == 4
    assert [item.candidate_id for item in first] == sorted(item.candidate_id for item in first)
    assert [item.fingerprint for item in first] == [item.fingerprint for item in second]
    assert all("eval" not in item.expression for item in first)

