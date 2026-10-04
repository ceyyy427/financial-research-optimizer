from __future__ import annotations

import pandas as pd
import pytest

from finahinking.data.models import Dataset, Provenance
from finahinking.p6_6 import (
    FeatureDefinition,
    FeatureGraph,
    FeatureNode,
    FeatureRegistry,
    FeatureVersion,
    PointInTimeViolation,
    StrategyCompiler,
    StrategyInterpreter,
    StrategyVersion,
    compile_strategy,
    generate_educational_code,
    learning_cards,
    review_strategy,
    scan_educational_code,
)


def _accepted(idea: str):
    return StrategyInterpreter().accept(review_strategy(idea)).spec


def test_feature_versions_and_graph_are_fingerprinted_and_acyclic() -> None:
    definition = FeatureDefinition("x", "X", "test", "return", "close.pct_change(1)", input_fields=("close",), version="v1")
    version = FeatureVersion(definition)
    graph = FeatureGraph((FeatureNode("x", version),), ("x",))
    assert len(version.fingerprint) == 64
    assert len(graph.fingerprint) == 64
    with pytest.raises(ValueError, match="cycle"):
        FeatureGraph((FeatureNode("a", version, ("b",)), FeatureNode("b", version, ("a",))), ("a",))


def test_registry_is_allow_listed_and_point_in_time_safe() -> None:
    registry = FeatureRegistry().register(FeatureDefinition("mean", "Mean", "test", "rolling_mean", "close.rolling(3).mean()", input_fields=("close",), window=3))
    frame = pd.DataFrame({"close": [1.0, 2.0, 3.0], "available_at": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"])}, index=pd.date_range("2020-01-01", periods=3))
    values = registry.evaluate("mean", frame)
    assert values.iloc[-1] == pytest.approx(2.0)
    late = frame.copy()
    late.iloc[0, late.columns.get_loc("available_at")] = pd.Timestamp("2020-01-02")
    with pytest.raises(PointInTimeViolation):
        registry.evaluate("mean", late)


def test_review_requires_explicit_acceptance_and_compiles_to_ir() -> None:
    review = review_strategy("Use lagged momentum and low volatility")
    with pytest.raises(ValueError, match="reviewed"):
        StrategyCompiler().compile_ir(review.spec)
    spec = StrategyInterpreter().accept(review).spec
    ir, compiled = compile_strategy(spec)
    assert compiled is None  # panel template is dispatched by the P5.5 adapter
    assert all(node.kind in {"feature_ref", "compare", "boolean", "rank", "selection", "target_weight", "rebalance", "next_period_execution"} for node in ir.nodes)
    assert len(ir.fingerprint) == 64
    with pytest.raises(ValueError, match="reviewed"):
        StrategyVersion(review.spec)


def test_moving_average_compiles_to_p5_strategy_protocol() -> None:
    spec = _accepted("Use a moving average trend rule")
    ir, compiled = compile_strategy(spec)
    assert compiled is not None
    data = Dataset(pd.DataFrame({"close": range(1, 41)}, index=pd.date_range("2020-01-01", periods=40)), Provenance("test", "https://example.test"))
    weights = compiled.generate(data)
    assert weights.index.equals(data.frame.index)
    assert weights.max() <= 1.0
    assert ir.strategy_version.version == spec.version


def test_educational_code_is_static_and_learning_cards_trace_evidence() -> None:
    spec = _accepted("Use a moving average trend rule")
    ir, _ = compile_strategy(spec)
    generated = generate_educational_code(spec, ir)
    assert generated.safety.safe
    assert "import " not in generated.source
    assert scan_educational_code("import os\nopen('bad', 'w')").safe is False
    cards = learning_cards(spec, ir)
    assert len(cards) >= 5
    assert all(card.evidence_reference == f"strategy:{spec.strategy_id}:{spec.version}" for card in cards)
