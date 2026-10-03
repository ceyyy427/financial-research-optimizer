from __future__ import annotations

import pytest

from finahinking.p8_2b.catalog import get_knowledge_unit
from finahinking.p8_2b.pedagogy import LearningDepth, learning_sequence, record_learning_evidence


def test_quick_and_deep_sequences_are_progressive_and_page_view_is_not_mastery() -> None:
    unit = get_knowledge_unit("ols")
    assert learning_sequence(unit, LearningDepth.QUICK) == ("why_now", "intuition", "current_data")
    deep = learning_sequence(unit, LearningDepth.TEACH_ME)
    assert deep[0] == "why_now" and "derivation" in deep and deep[-1] == "literature"
    with pytest.raises(ValueError, match="exercise"):
        record_learning_evidence(unit, "research-1", None, "correct")


def test_explicit_exercise_evidence_is_auditable() -> None:
    evidence = record_learning_evidence(get_knowledge_unit("sharpe"), "research-1", "exercise-1", "correct")
    assert evidence["event_type"] == "exercise_result"
    assert evidence["mastery_inferred"] is False
    assert evidence["evidence_reference"] == "knowledge:sharpe:exercise-1:research-1"
