"""Small inspectable P7 product-surface facade for local vertical slices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context import EvidenceGroundedGuidance, GuidanceResult
from .personal import MisconceptionContinuity, PersonalIntelligenceService, TimelineEvent
from .workflows import (
    StrategyJourneyInput,
    StrategyJourneyResult,
    StrategyPersonalCommunityWorkflow,
)


@dataclass(frozen=True)
class PersonalHomeSnapshot:
    """Progressive-disclosure data for one authenticated principal."""

    principal_id: str
    context: tuple[dict[str, Any], ...]
    timeline: tuple[TimelineEvent, ...]
    misconceptions: tuple[MisconceptionContinuity, ...]
    mastery: tuple[dict[str, Any], ...]
    guidance: GuidanceResult


class PersonalHomeService:
    """Render a bounded private home without creating a second data store."""

    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self.personal = PersonalIntelligenceService(repository)
        self.guidance = EvidenceGroundedGuidance(repository)
        self.workflow = StrategyPersonalCommunityWorkflow(repository)

    def snapshot(self, session_id: str, *, purpose: str = "personal home", limit: int = 50) -> PersonalHomeSnapshot:
        principal_id = self.repository._principal(session_id)
        context = tuple(self.repository.authorized_context(session_id, purpose=purpose, limit=limit))
        timeline = self.personal.timeline(session_id, limit=limit)
        misconceptions = self.personal.list_misconceptions(session_id)
        export = self.repository.export_personal(session_id)
        guidance = self.guidance.suggest(session_id, purpose=purpose, limit=3)
        return PersonalHomeSnapshot(principal_id, context, timeline, misconceptions, tuple(export.get("mastery", ())), guidance)

    def run_strategy_journey(self, journey: StrategyJourneyInput, *, create_missing_concepts: bool = False) -> StrategyJourneyResult:
        return self.workflow.run(journey, create_missing_concepts=create_missing_concepts)


ProductSurface = PersonalHomeService


__all__ = ["PersonalHomeService", "PersonalHomeSnapshot", "ProductSurface"]
