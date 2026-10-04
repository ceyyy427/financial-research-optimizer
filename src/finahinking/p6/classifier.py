"""Deterministic task classifier for P6 intake."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import ResearchQuestion, TaskCategory


@dataclass(frozen=True)
class Classification:
    category: TaskCategory
    reason: str
    signals: tuple[str, ...] = ()
    confidence: float = 0.8
    required_clarifications: tuple[str, ...] = ()
    material_assumptions: tuple[str, ...] = ()
    classifier_version: str = "p6-classifier-v1"

    def __post_init__(self) -> None:
        if not isinstance(self.category, TaskCategory):
            object.__setattr__(self, "category", TaskCategory(self.category))
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("classification reason is required")
        object.__setattr__(self, "signals", tuple(str(value) for value in self.signals))
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("classification confidence must be between zero and one")
        object.__setattr__(self, "required_clarifications", tuple(str(value) for value in self.required_clarifications))
        object.__setattr__(self, "material_assumptions", tuple(str(value) for value in self.material_assumptions))
        if not isinstance(self.classifier_version, str) or not self.classifier_version.strip():
            raise ValueError("classifier_version is required")

    @property
    def task_category(self) -> TaskCategory:
        return self.category

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "category": self.category.value,
            "reason": self.reason,
            "signals": list(self.signals),
            "confidence": self.confidence,
            "required_clarifications": list(self.required_clarifications),
            "material_assumptions": list(self.material_assumptions),
            "classifier_version": self.classifier_version,
        }


_RULES: tuple[tuple[TaskCategory, tuple[str, ...], str], ...] = (
    (TaskCategory.STAND_BACK, ("should i buy", "should i sell", "buy this stock", "sell this stock", "place an order", "execute a trade", "live trading", "automatic trading", "find the best strategy", "optimize the portfolio", "ignore prior", "bypass policy", "delete the artifact", "pip install"), "investment action, prompt injection, or unbounded search requires human judgment"),
    (TaskCategory.EVIDENCE, ("source evidence", "show the evidence", "cite the source", "where is the evidence", "provide sources"), "the user requests evidence"),
    (TaskCategory.LEARN, ("what is a sharpe", "what does sharpe", "explain sharpe", "what is beta", "explain beta", "what is regression", "explain regression", "explain risk", "what is volatility", "what is a p-value", "define ", "what is momentum", "teach me", "teach"), "the user requests a concept explanation"),
    (TaskCategory.QUESTION, ("which dataset", "what dataset", "which period", "what period", "which question", "what should i investigate", "what can we test", "can you clarify", "please clarify", "not sure which", "what do you mean"), "a research boundary is missing and needs clarification"),
    (TaskCategory.GUIDE, ("how do i", "how should i", "walk me through", "guide me", "how to", "steps to"), "the user requests procedural guidance"),
    (TaskCategory.HISTORY, ("history of", "historical development", "who invented", "when did"), "the user requests historical context"),
    (TaskCategory.QUANT, ("backtest", "dataset", "momentum work", "regression", "beta", "sensitive", "sensitivity", "market return", "factor", "returns", "volatility", "risk", "benchmark", "performance", "does .* work"), "an approved quantitative experiment may answer the question"),
)


def classify_question(question: ResearchQuestion | str) -> Classification:
    text = question.question if isinstance(question, ResearchQuestion) else str(question)
    cleaned = " ".join(text.casefold().split())
    if not cleaned:
        raise ValueError("question is required")
    for category, terms, reason in _RULES:
        matched = tuple(term for term in terms if (term in cleaned or (term == "does .* work" and cleaned.startswith("does ") and " work" in cleaned)))
        if matched:
            confidence = 0.97 if category is TaskCategory.STAND_BACK else 0.9
            clarifications = ("name the dataset and evaluation period",) if category is TaskCategory.QUESTION else ()
            assumptions = ("use an approved deterministic service",) if category is TaskCategory.QUANT else ()
            return Classification(category, reason, matched, confidence, clarifications, assumptions)
    if (
        cleaned in {"help", "can you help", "what should i do", "what should we do", "i need help"}
        or cleaned.startswith(("can you help ", "i need help "))
    ):
        return Classification(
            TaskCategory.QUESTION,
            "the request is ambiguous and needs a bounded research target",
            (),
            0.45,
            ("state the concept, evidence, or dataset you want to examine",),
        )
    return Classification(TaskCategory.ANSWER, "a bounded explanatory answer is appropriate", (), 0.55)


class TaskClassifier:
    def classify(self, question: ResearchQuestion | str) -> Classification:
        return classify_question(question)


__all__ = ["Classification", "TaskClassifier", "classify_question"]
