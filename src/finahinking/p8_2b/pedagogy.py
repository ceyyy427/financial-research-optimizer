"""Progressive learning sequences with explicit evidence boundaries."""

from __future__ import annotations

from enum import Enum

from .contracts import KnowledgeUnit


class LearningDepth(str, Enum):
    QUICK = "QUICK"
    TEACH_ME = "TEACH_ME"


def learning_sequence(unit: KnowledgeUnit, depth: LearningDepth) -> tuple[str, ...]:
    if depth == LearningDepth.QUICK:
        return ("why_now", "intuition", "current_data")
    return ("why_now", "prerequisites", "background", "intuition", "definition", "symbols", "equations", "derivation", "proof", "assumptions", "controlled_example", "code", "current_data", "exercise", "literature")


def record_learning_evidence(unit: KnowledgeUnit, context_id: str, exercise_id: str | None, outcome: str) -> dict[str, object]:
    if not exercise_id:
        raise ValueError("exercise is required for learning evidence")
    if outcome not in {"correct", "incorrect", "skipped"}:
        raise ValueError("outcome is invalid")
    return {"event_type": "exercise_result", "knowledge_unit_id": unit.unit_id, "context_id": context_id, "exercise_id": exercise_id, "outcome": outcome, "mastery_inferred": False, "evidence_reference": f"knowledge:{unit.unit_id}:{exercise_id}:{context_id}"}
