"""Server-owned context bindings for current research and learning."""

from __future__ import annotations

from dataclasses import dataclass

from .contracts import KnowledgeContextBinding, KnowledgeUnit


@dataclass(frozen=True)
class ContextSnapshot:
    context_type: str
    context_id: str
    context_time: str
    available_at: str
    dataset_fingerprint: str
    current_values: tuple[dict[str, object], ...]
    evidence_ids: tuple[str, ...]
    feature_id: str | None
    research_run_id: str | None
    source_state: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ContextResolution:
    status: str
    binding: KnowledgeContextBinding | None


def resolve_context(unit: KnowledgeUnit, snapshot: ContextSnapshot, *, unit_id: str | None = None) -> ContextResolution:
    if unit_id is not None and unit_id != unit.unit_id:
        raise KeyError(unit_id)
    if snapshot.context_type not in {"event", "research_point", "research_run", "quant_run", "feature", "strategy"}:
        raise ValueError("context_type is invalid")
    binding = KnowledgeContextBinding(unit.unit_id, snapshot.context_type, snapshot.context_id, f"Why now: {unit.why_now}", snapshot.current_values, snapshot.evidence_ids, snapshot.feature_id, snapshot.research_run_id, snapshot.context_time, snapshot.available_at, snapshot.dataset_fingerprint, snapshot.source_state, snapshot.limitations)
    return ContextResolution("AVAILABLE", binding)


def no_context() -> ContextResolution:
    return ContextResolution("NO_CONTEXT_AVAILABLE", None)
