"""Ordered state machine for a single guided research session."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .models import P6State

_ORDER = (
    P6State.QUESTION_RECEIVED,
    P6State.CLASSIFIED,
    P6State.HYPOTHESIS_PROPOSED,
    P6State.EXPERIMENT_PROPOSED,
    P6State.ASSUMPTIONS_ACCEPTED,
    P6State.TOOL_EXECUTED,
    P6State.EVIDENCE_READY,
    P6State.EXPLANATION_READY,
    P6State.LEARNING_READY,
)


@dataclass(frozen=True)
class StateTransition:
    from_state: P6State
    to_state: P6State
    actor: str = "application"
    input_fingerprint: str | None = None
    occurred_at: str = ""

    def __post_init__(self) -> None:
        if not self.occurred_at:
            object.__setattr__(self, "occurred_at", datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, str | None]:
        return {"from": self.from_state.value, "to": self.to_state.value, "actor": self.actor,
                "input_fingerprint": self.input_fingerprint, "occurred_at": self.occurred_at}


class GuidedStateMachine:
    """Enforce the no-skipping P6 lifecycle.

    A new machine starts after question intake.  Each transition is exactly
    one edge in the ordered lifecycle; this makes it impossible to execute a
    tool before the explicit assumptions review.
    """

    def __init__(self, state: P6State = P6State.QUESTION_RECEIVED) -> None:
        self._state = state if isinstance(state, P6State) else P6State(state)
        self._history: list[StateTransition] = []

    @property
    def state(self) -> P6State:
        return self._state

    @property
    def history(self) -> tuple[StateTransition, ...]:
        return tuple(self._history)

    def transition(
        self,
        state: P6State,
        *,
        actor: str = "application",
        input_fingerprint: str | None = None,
        occurred_at: str | None = None,
    ) -> P6State:
        target = state if isinstance(state, P6State) else P6State(state)
        if target in {P6State.REJECTED, P6State.FAILED, P6State.CANCELLED}:
            if self._state in {P6State.LEARNING_READY, P6State.REJECTED, P6State.FAILED, P6State.CANCELLED}:
                raise ValueError("terminal state cannot be changed")
            self._history.append(StateTransition(self._state, target, actor, input_fingerprint, occurred_at or ""))
            self._state = target
            return self._state
        try:
            expected = _ORDER[_ORDER.index(self._state) + 1]
        except (ValueError, IndexError) as exc:
            raise ValueError("transition is not available from the current state") from exc
        if target is not expected:
            raise ValueError(f"invalid transition: {self._state.value} -> {target.value}; expected {expected.value}")
        self._history.append(StateTransition(self._state, target, actor, input_fingerprint, occurred_at or ""))
        self._state = target
        return self._state

    def can_transition(self, state: P6State) -> bool:
        try:
            target = state if isinstance(state, P6State) else P6State(state)
            if target in {P6State.REJECTED, P6State.FAILED, P6State.CANCELLED}:
                return self._state not in {P6State.LEARNING_READY, P6State.REJECTED, P6State.FAILED, P6State.CANCELLED}
            return _ORDER.index(target) == _ORDER.index(self._state) + 1
        except (ValueError, IndexError):
            return False

    def reject(self, *, actor: str = "policy", input_fingerprint: str | None = None) -> P6State:
        return self.transition(P6State.REJECTED, actor=actor, input_fingerprint=input_fingerprint)

    def fail(self, *, actor: str = "application", input_fingerprint: str | None = None) -> P6State:
        return self.transition(P6State.FAILED, actor=actor, input_fingerprint=input_fingerprint)

    def cancel(self, *, actor: str = "user", input_fingerprint: str | None = None) -> P6State:
        return self.transition(P6State.CANCELLED, actor=actor, input_fingerprint=input_fingerprint)

    def to_dict(self) -> dict[str, Any]:
        return {"state": self.state.value, "history": [item.to_dict() for item in self.history]}


P6StateMachine = GuidedStateMachine
SessionStateMachine = GuidedStateMachine

__all__ = ["GuidedStateMachine", "P6StateMachine", "SessionStateMachine", "StateTransition"]
