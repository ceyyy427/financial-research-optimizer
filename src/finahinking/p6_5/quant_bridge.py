"""Event-to-quant bridge that consumes the frozen P6 typed gateway."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from finahinking.p6.gateway import P6QuantGateway
from finahinking.p6.hypothesis import build_hypothesis
from finahinking.p6.models import ResearchQuestion, TypedToolRequest, TypedToolResponse
from finahinking.p6.planner import plan_experiment

from .models import Event


class EventQuantBridge:
    """Translate one event into a bounded, auditable P6 tool request.

    This class intentionally contains no quant runtime.  It creates a P6
    experiment plan, accepts the explicit assumptions required by that plan,
    and invokes only ``P6QuantGateway.execute``.
    """

    def __init__(self, gateway: P6QuantGateway | None = None) -> None:
        self.gateway = gateway or P6QuantGateway()

    @staticmethod
    def fixture_frame() -> pd.DataFrame:
        rows: list[dict[str, Any]] = []
        values = {
            "2020-01-01": (100.0, 100.0),
            "2020-01-02": (110.0, 95.0),
            "2020-01-03": (121.0, 90.0),
            "2020-01-04": (120.0, 92.0),
            "2020-01-05": (130.0, 88.0),
        }
        for date, (aaa, bbb) in values.items():
            rows.extend(
                [
                    {"date": date, "asset": "AAA", "close": aaa, "available_at": date},
                    {"date": date, "asset": "BBB", "close": bbb, "available_at": date},
                ]
            )
        return pd.DataFrame(rows)

    def run(self, event: Event, user_id: str, *, frame: pd.DataFrame | None = None) -> TypedToolResponse:
        if not isinstance(event, Event):
            raise TypeError("event is required")
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id is required")
        question = ResearchQuestion(
            "Does momentum work in the historical context of this CPI release?",
            user_id=user_id,
        )
        hypothesis = build_hypothesis(question)
        specification = plan_experiment(hypothesis, dataset_id=f"p6-5-{event.reference_period}")
        self.gateway.register_plan(specification)
        source_frame = frame if frame is not None else self.fixture_frame()
        if not isinstance(source_frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame")
        rows = json.loads(source_frame.to_json(orient="records"))
        request = TypedToolRequest(
            "quant.run_backtest",
            {"rows": rows, "question": question.question, "hypothesis": hypothesis.statement},
            request_id=f"p6-5-quant-{event.reference_period.replace('-', '')}",
            experiment_fingerprint=specification.fingerprint,
            assumptions_accepted=True,
            provenance_context={"workflow": "p6-5-cpi-vertical-slice", "event_id": event.event_id},
        )
        response = self.gateway.execute(request)
        return response


__all__ = ["EventQuantBridge"]
