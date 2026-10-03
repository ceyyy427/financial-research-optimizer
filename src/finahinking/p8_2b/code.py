"""Static code-to-math-to-data inspection; no execution path."""

from __future__ import annotations

from .contracts import CodeSegment, KnowledgeUnit
from .validation import validate_code


def select_code_segment(unit: KnowledgeUnit, segment_id: str, *, source_override: str | None = None) -> CodeSegment:
    segment = next((item for item in unit.code_segments if item.segment_id == segment_id), None)
    if segment is None:
        raise KeyError(segment_id)
    if source_override is not None:
        validate_code(source_override)
    return segment


def trace_code_to_data(unit: KnowledgeUnit, segment_id: str) -> dict[str, object]:
    segment = select_code_segment(unit, segment_id)
    return {"segment_id": segment.segment_id, "line_range": list(segment.line_range), "code": segment.code, "equation_ids": list(segment.equation_ids), "feature_ids": list(segment.feature_ids), "data_input": segment.data_input, "data_output": segment.data_output, "finance_role": unit.applications[0] if unit.applications else "research explanation", "limitations": list(unit.limitations)}
