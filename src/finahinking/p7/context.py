"""Evidence-grounded, non-advisory personal guidance for P7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .personal import PersonalIntelligenceService


def _text(value: Any, label: str, limit: int = 512) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    value = value.strip()
    if len(value) > limit:
        raise ValueError(f"{label} is too long")
    return value


@dataclass(frozen=True)
class GuidanceSuggestion:
    """A bounded optional next interaction, never a trading instruction."""

    suggestion_id: str
    text: str
    evidence_ids: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    context_node_ids: tuple[str, ...] = ()
    optional: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "suggestion_id", _text(self.suggestion_id, "suggestion_id"))
        object.__setattr__(self, "text", _text(self.text, "text", 2_000))
        object.__setattr__(self, "evidence_ids", tuple(_text(item, "evidence_id") for item in self.evidence_ids))
        object.__setattr__(self, "limitations", tuple(_text(item, "limitation") for item in self.limitations))
        object.__setattr__(self, "context_node_ids", tuple(_text(item, "context_node_id") for item in self.context_node_ids))
        if self.optional is not True:
            raise ValueError("personal guidance must remain optional")

    def lower(self) -> str:
        """Return display text in lowercase for simple UI assertions."""
        return self.text.lower()


@dataclass(frozen=True)
class GuidanceResult:
    purpose: str
    suggestions: tuple[GuidanceSuggestion, ...]
    evidence_ids: tuple[str, ...]
    limitations: tuple[str, ...]
    context_node_ids: tuple[str, ...]
    truth_preserved: bool = True
    disclaimer: str = "Guidance can change explanation order or review prompts, not evidence or quantitative results."

    def __post_init__(self) -> None:
        object.__setattr__(self, "purpose", _text(self.purpose, "purpose"))
        object.__setattr__(self, "suggestions", tuple(self.suggestions))
        object.__setattr__(self, "evidence_ids", tuple(_text(item, "evidence_id") for item in self.evidence_ids))
        object.__setattr__(self, "limitations", tuple(_text(item, "limitation") for item in self.limitations))
        object.__setattr__(self, "context_node_ids", tuple(_text(item, "context_node_id") for item in self.context_node_ids))
        if self.truth_preserved is not True:
            raise ValueError("guidance cannot mark truth as personalized")
        object.__setattr__(self, "disclaimer", _text(self.disclaimer, "disclaimer", 2_000))

    def to_dict(self) -> dict[str, Any]:
        return {
            "purpose": self.purpose,
            "suggestions": [
                {
                    "suggestion_id": suggestion.suggestion_id,
                    "text": suggestion.text,
                    "evidence_ids": list(suggestion.evidence_ids),
                    "limitations": list(suggestion.limitations),
                    "context_node_ids": list(suggestion.context_node_ids),
                    "optional": suggestion.optional,
                }
                for suggestion in self.suggestions
            ],
            "evidence_ids": list(self.evidence_ids),
            "limitations": list(self.limitations),
            "context_node_ids": list(self.context_node_ids),
            "truth_preserved": self.truth_preserved,
            "disclaimer": self.disclaimer,
        }


class EvidenceGroundedGuidance:
    """Derive optional prompts from owner-authorized, inspectable evidence.

    This class intentionally does not accept a free-form model response or a
    numeric "user score".  It reads the repository's explicit mastery and
    misconception records and returns their references beside every prompt.
    """

    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self.personal = PersonalIntelligenceService(repository)

    def suggest(
        self,
        session_id: str,
        *,
        purpose: str,
        question: str | None = None,
        limit: int = 3,
    ) -> GuidanceResult:
        purpose = _text(purpose, "purpose")
        if question is not None:
            question = _text(question, "question", 2_000)
        bounded = max(1, min(int(limit), 10))
        context = self.repository.authorized_context(session_id, purpose=purpose, limit=max(1, bounded * 3))
        context_ids = {str(item["node_id"]) for item in context[:bounded]}
        exported = self.repository.export_personal(session_id)
        suggestions: list[GuidanceSuggestion] = []
        all_evidence: list[str] = []
        all_limitations: list[str] = []
        for item in context:
            payload = item.get("payload", {})
            all_limitations.extend(str(value) for value in payload.get("limitations", ()))
        for item in exported.get("history", ()):
            all_limitations.extend(str(value) for value in item.get("limitations", ()))

        # A NEEDS_REVIEW mastery state is an explicit evidence-backed reason to
        # offer a review prompt.  It is not an opaque ranking or recommendation.
        for state in exported.get("mastery", ()):
            if state.get("state") != "NEEDS_REVIEW":
                continue
            concept_id = str(state["concept_id"])
            evidence_ids = tuple(str(item) for item in state.get("evidence_ids", ()))
            all_evidence.extend(evidence_ids)
            try:
                concept = self.repository.get_node(session_id, concept_id)
                title = concept.title
            except KeyError:
                title = concept_id
            if concept_id not in context_ids:
                # Keep the returned context bounded to the explicitly used
                # evidence, but still include the concept for inspectability.
                context_ids.add(concept_id)
            suggestions.append(
                GuidanceSuggestion(
                    f"review:{concept_id}",
                    f"Would you like to review {title} before continuing {purpose}? "
                    f"The stored mastery explanation is: {state['explanation']}",
                    evidence_ids,
                    tuple(str(item) for item in state.get("limitations", ())),
                    (concept_id,),
                )
            )
            if len(suggestions) >= bounded:
                break

        # Open misconceptions remain useful even when their concept has not
        # yet acquired enough mastery evidence for NEEDS_REVIEW.
        if len(suggestions) < bounded:
            for misconception in self.personal.list_misconceptions(session_id, status="OPEN"):
                evidence_ids = (misconception.evidence_reference,)
                all_evidence.extend(evidence_ids)
                if misconception.misconception_id not in context_ids:
                    context_ids.add(misconception.misconception_id)
                suggestions.append(
                    GuidanceSuggestion(
                        f"misconception:{misconception.misconception_id}",
                        f"Would you like to inspect the evidence behind the open review item "
                        f"‘{misconception.observed_statement}’ before interpreting new results? "
                        f"The recorded correction is: {misconception.correction}",
                        evidence_ids,
                        (),
                        (misconception.misconception_id, misconception.concept_id),
                    )
                )
                if len(suggestions) >= bounded:
                    break

        if not suggestions:
            prompt = "No evidence-linked review item is currently due. Choose a concept or artifact to inspect next."
            if question:
                prompt = f"No evidence-linked review item is currently due for ‘{question}’. Choose an artifact to inspect next."
            suggestions.append(GuidanceSuggestion("inspect-next", prompt, (), (), ()))

        # Stable, duplicate-free evidence references make audit and UI display
        # deterministic across repeated calls.
        dedup_evidence = tuple(dict.fromkeys(all_evidence))
        dedup_context = tuple(sorted(context_ids))
        return GuidanceResult(
            purpose,
            tuple(suggestions[:bounded]),
            dedup_evidence,
            tuple(dict.fromkeys(all_limitations)),
            dedup_context,
        )


PersonalGuidance = EvidenceGroundedGuidance
Guidance = GuidanceResult
GuidanceService = EvidenceGroundedGuidance


def suggest_guidance(repository: Any, session_id: str, *, purpose: str, question: str | None = None, limit: int = 3) -> GuidanceResult:
    return EvidenceGroundedGuidance(repository).suggest(session_id, purpose=purpose, question=question, limit=limit)


__all__ = [
    "EvidenceGroundedGuidance",
    "Guidance",
    "GuidanceResult",
    "GuidanceService",
    "GuidanceSuggestion",
    "PersonalGuidance",
    "suggest_guidance",
]
