"""Mechanism maps and conclusion ladder for progressive disclosure."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import Concept, ConceptRelation, EvidenceStatus


@dataclass(frozen=True)
class WhyItMatters:
    event_id: str
    statement: str
    mechanism: str
    relation_type: str
    evidence_status: EvidenceStatus
    evidence_ids: tuple[str, ...]
    limitation: str

    def __post_init__(self) -> None:
        if self.relation_type not in {"ECONOMIC_MECHANISM", "SUPPORTED_RELATIONSHIP", "HISTORICAL_ASSOCIATION", "HYPOTHESIS"}:
            raise ValueError("relation type is invalid")
        if not self.evidence_ids:
            raise ValueError("why-it-matters requires evidence ids")
        if not self.limitation.strip():
            raise ValueError("why-it-matters requires a limitation")
        if not isinstance(self.evidence_status, EvidenceStatus):
            object.__setattr__(self, "evidence_status", EvidenceStatus(self.evidence_status))

    def to_dict(self) -> dict[str, object]:
        return {"event_id": self.event_id, "statement": self.statement, "mechanism": self.mechanism, "relation_type": self.relation_type, "evidence_status": self.evidence_status.value, "evidence_ids": list(self.evidence_ids), "limitation": self.limitation}


class ConclusionLevel(str, Enum):
    WHAT_WE_KNOW = "WHAT_WE_KNOW"
    EVIDENCE_SUGGESTS = "EVIDENCE_SUGGESTS"
    PLAUSIBLE = "PLAUSIBLE"
    UNKNOWN = "UNKNOWN"
    WHAT_WOULD_CHANGE_VIEW = "WHAT_WOULD_CHANGE_VIEW"


@dataclass(frozen=True)
class ConclusionEntry:
    level: ConclusionLevel
    text: str
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.level, ConclusionLevel):
            object.__setattr__(self, "level", ConclusionLevel(self.level))
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("conclusion text is required")
        object.__setattr__(self, "evidence_ids", tuple(str(value) for value in self.evidence_ids))


@dataclass(frozen=True)
class ConclusionLadder:
    entries: tuple[ConclusionEntry | tuple[ConclusionLevel, str, tuple[str, ...]], ...]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        normalized = []
        for entry in self.entries:
            if isinstance(entry, ConclusionEntry):
                normalized.append(entry)
            else:
                level, text, evidence_ids = entry
                normalized.append(ConclusionEntry(level, text, tuple(evidence_ids)))
        expected = tuple(ConclusionLevel)
        if tuple(item.level for item in normalized) != expected:
            raise ValueError("conclusion ladder levels must be ordered and complete")
        if not self.limitations or any(not str(value).strip() for value in self.limitations):
            raise ValueError("conclusion ladder requires limitations")
        object.__setattr__(self, "entries", tuple(normalized))
        object.__setattr__(self, "limitations", tuple(str(value) for value in self.limitations))

    def level(self, level: ConclusionLevel) -> ConclusionEntry:
        return next(entry for entry in self.entries if entry.level is level)

    def to_dict(self) -> dict[str, object]:
        return {"entries": [{"level": entry.level.value, "text": entry.text, "evidence_ids": list(entry.evidence_ids)} for entry in self.entries], "limitations": list(self.limitations)}


@dataclass(frozen=True)
class KnowledgeBridge:
    event_id: str
    concepts: tuple[Concept, ...]
    relations: tuple[ConceptRelation, ...]

    def __post_init__(self) -> None:
        ids = {concept.concept_id for concept in self.concepts}
        if len(ids) != len(self.concepts):
            raise ValueError("concept ids must be unique")
        allowed = {"ECONOMIC_MECHANISM", "SUPPORTED_RELATIONSHIP", "HISTORICAL_ASSOCIATION", "HYPOTHESIS"}
        for relation in self.relations:
            if relation.from_concept_id not in ids or relation.to_concept_id not in ids:
                raise ValueError("relation references an unknown concept")
            if relation.relation_type not in allowed:
                raise ValueError("relation type is invalid")
        object.__setattr__(self, "concepts", tuple(self.concepts))
        object.__setattr__(self, "relations", tuple(self.relations))

    def path(self) -> tuple[Concept, ...]:
        return self.concepts

    def to_dict(self) -> dict[str, object]:
        return {"event_id": self.event_id, "concepts": [concept.to_dict() for concept in self.concepts], "relations": [relation.to_dict() for relation in self.relations]}


@dataclass(frozen=True)
class HistoricalAnalogue:
    reference_period: str
    similarity_dimensions: tuple[str, ...]
    difference_dimensions: tuple[str, ...]
    economic_regime: str
    rate_environment: str
    observed_result: str
    limitation: str = "Historical analogy does not imply repetition."

    def __post_init__(self) -> None:
        if not self.similarity_dimensions or not self.difference_dimensions:
            raise ValueError("an analogue requires similarities and differences")
        if "does not imply repetition" not in self.limitation.casefold():
            raise ValueError("analogue limitation must reject repetition claims")


__all__ = ["ConclusionEntry", "ConclusionLadder", "ConclusionLevel", "HistoricalAnalogue", "KnowledgeBridge", "WhyItMatters"]
