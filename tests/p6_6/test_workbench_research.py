from __future__ import annotations

import pytest

from finahinking.p6_6.workbench import ResearchCharter
from finahinking.p6_6.workbench_research import (
    FactorGraphSpec,
    ResearchSession,
    WorkbenchStore,
    evaluate_factor_graph,
)


def charter(max_experiments: int = 2) -> ResearchCharter:
    return ResearchCharter(
        "charter-research",
        "Does lagged momentum survive costs?",
        "lagged price return",
        "fixture",
        {"train": "2026-01", "validation": "2026-02", "test": "2026-03"},
        ("oos_return",),
        {"paper_only": True},
        ("input", "return", "rolling", "lag", "rank", "combine"),
        max_experiments=max_experiments,
        iteration_budget=max_experiments,
    )


def test_factor_graph_accepts_allowlisted_primitives_and_evaluates_point_in_time() -> None:
    graph = FactorGraphSpec(
        "momentum", "v1",
        nodes=(
            {"id": "close", "primitive": "input", "field": "close"},
            {"id": "ret", "primitive": "return", "inputs": ("close",), "window": 1},
            {"id": "lagged", "primitive": "lag", "inputs": ("ret",), "periods": 1},
        ),
        outputs=("lagged",),
    )
    rows = [
        {"time": "2026-01-01", "instrument": "AAA", "close": 100, "available_at": "2026-01-01"},
        {"time": "2026-01-02", "instrument": "AAA", "close": 110, "available_at": "2026-01-02"},
        {"time": "2026-01-03", "instrument": "AAA", "close": 121, "available_at": "2026-01-03"},
    ]
    evaluated = evaluate_factor_graph(graph, rows)
    assert evaluated[0]["factors"]["lagged"] is None
    assert evaluated[1]["factors"]["lagged"] is None
    assert evaluated[2]["factors"]["lagged"] == pytest.approx(0.1)
    assert evaluated[2]["factors"]["available_at"] == "2026-01-02"


def test_factor_graph_rejects_unknown_primitive_cycle_and_future_availability() -> None:
    with pytest.raises(ValueError, match="primitive"):
        FactorGraphSpec("bad", "v1", nodes=({"id": "x", "primitive": "shell"},), outputs=("x",))
    with pytest.raises(ValueError, match="cycle"):
        FactorGraphSpec("cycle", "v1", nodes=({"id": "a", "primitive": "combine", "inputs": ("b",)}, {"id": "b", "primitive": "combine", "inputs": ("a",)}), outputs=("a",))
    with pytest.raises(ValueError, match="available"):
        evaluate_factor_graph(FactorGraphSpec("pit", "v1", nodes=({"id": "c", "primitive": "input", "field": "close"},), outputs=("c",)), [{"time": "2026-01-01", "instrument": "AAA", "close": 100, "available_at": "2026-01-02"}])


def test_research_session_preserves_failed_attempts_and_freezes_test_once() -> None:
    session = ResearchSession.start("session-1", charter())
    session = session.record_attempt("candidate-1", "REJECTED", {"reason": "costs dominate"})
    session = session.record_attempt("candidate-2", "KEEP", {"validation": 0.1})
    assert len(session.attempts) == 2
    with pytest.raises(ValueError, match="budget"):
        session.record_attempt("candidate-3", "REJECTED", {})
    frozen = session.freeze("candidate-2")
    assert frozen.state == "STRATEGY_FROZEN"
    frozen = frozen.evaluate_test({"oos_return": 0.04})
    assert frozen.state == "TEST_EVALUATED"
    with pytest.raises(ValueError, match="once"):
        frozen.evaluate_test({"oos_return": 0.05})


def test_test_data_is_hidden_before_freeze_and_store_can_reopen_or_rollback() -> None:
    session = ResearchSession.start("session-2", charter(3))
    with pytest.raises(ValueError, match="test"):
        session.evaluate_test({"oos_return": 0.1})
    store = WorkbenchStore()
    version_one = store.save(session)
    updated = session.record_attempt("candidate-1", "REJECTED", {"validation": -0.1})
    version_two = store.save(updated)
    assert store.open(version_one).fingerprint == session.fingerprint
    assert store.rollback(version_two).fingerprint == session.fingerprint
    assert store.history("session-2") == (version_one, version_two)


def test_session_rejects_unvalidated_proposal_and_test_metric_mutation() -> None:
    session = ResearchSession.start("session-3", charter())
    with pytest.raises(ValueError, match="status"):
        session.record_attempt("candidate", "BEST", {})
    with pytest.raises(ValueError, match="test"):
        session.record_attempt("candidate", "KEEP", {"test": 0.9})
