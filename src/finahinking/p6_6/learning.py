"""Learning integration for the P6.6 strategy lab.

The existing P6 learning contracts remain authoritative.  This adapter adds
the ordered Predict -> Reveal -> Explain interaction and binds each card to
the actual reviewed strategy fingerprint.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from finahinking.p6.explanation import PredictionRevealExplain, predict_reveal_explain
from finahinking.p6.learning import LearningCard, make_learning_card

from .education import StrategyLearningTrace
from .models import canonical_json


def _safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if hasattr(value, "to_dict"):
        return _safe(value.to_dict())
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class StrategyLearningBundle:
    evidence_reference: str
    strategy_fingerprint: str
    traces: tuple[StrategyLearningTrace, ...]
    cards: tuple[LearningCard, ...]
    interactions: tuple[PredictionRevealExplain, ...]

    @property
    def fingerprint(self) -> str:
        return _digest(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        payload = {"evidence_reference": self.evidence_reference, "strategy_fingerprint": self.strategy_fingerprint, "traces": [trace.to_dict() for trace in self.traces], "cards": [card.to_dict() for card in self.cards], "interactions": [event.to_dict() for event in self.interactions]}
        if include_fingerprint:
            payload["fingerprint"] = self.fingerprint
        return payload


def strategy_learning_bundle(strategy_spec: Any, *, strategy_fingerprint: str | None = None, evidence_reference: str | None = None, traces: tuple[StrategyLearningTrace, ...] | None = None, result: Mapping[str, Any] | None = None) -> StrategyLearningBundle:
    payload = _safe(strategy_spec)
    if not isinstance(payload, Mapping):
        payload = {"strategy": str(strategy_spec)}
    reference = evidence_reference or str(payload.get("dataset_reference") or payload.get("fingerprint") or "p6_6-strategy-research")
    fingerprint = strategy_fingerprint or str(payload.get("fingerprint") or _digest(payload))
    if traces is None:
        traces = (
            StrategyLearningTrace("timing", "series.shift(1)", "x_t uses information through t-1", "Lagging prevents future information from entering a signal.", "Prevent look-ahead bias.", "available_at timestamps are trusted.", "A timestamp check cannot prove source quality."),
            StrategyLearningTrace("costs", "turnover * (fee_bps + slippage_bps) / 10000", "net return = gross return - fees - slippage", "Turnover and friction can overwhelm a weak signal.", "Make costs visible.", "The reviewed config is applied deterministically.", "Actual market impact can differ."),
        )
    result_payload = dict(result or {"strategy_fingerprint": fingerprint, "research_reference": reference})
    result_payload.setdefault("fingerprint", _digest(result_payload))
    cards: list[LearningCard] = []
    interactions: list[PredictionRevealExplain] = []
    for trace in traces:
        component = getattr(trace, "component", getattr(trace, "component_id", "strategy_component"))
        math_text = getattr(trace, "math", getattr(trace, "math_explanation", ""))
        finance = getattr(trace, "finance", getattr(trace, "finance_explanation", ""))
        limitation = getattr(trace, "limitation", "Historical evidence is not a guarantee.")
        code_text = getattr(trace, "code", getattr(trace, "code_explanation", ""))
        context = {"evidence_reference": reference, "strategy_fingerprint": fingerprint, "component": component, "interpretation": finance}
        card = make_learning_card(concept=str(component), definition=str(math_text), formula=str(code_text), result_context=context, limitation=str(limitation), evidence_reference=reference, interpretation=str(finance), common_misconception="Historical evidence is not a promise of future returns.", follow_up_question="What additional evidence would change this conclusion?")
        cards.append(card)
        interactions.append(predict_reveal_explain(prompt=f"Predict how {component} affects the strategy.", prediction="It changes the simulated signal or net result.", result=result_payload, explanation=f"{code_text} {math_text} {finance}", evidence_reference=reference, result_fingerprint=result_payload["fingerprint"]))
    return StrategyLearningBundle(reference, fingerprint, tuple(traces), tuple(cards), tuple(interactions))


__all__ = ["StrategyLearningBundle", "strategy_learning_bundle"]
