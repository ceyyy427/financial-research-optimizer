from __future__ import annotations

import pytest

from finahinking.research.contracts import AgentReport, RiskReview
from finahinking.research.workflow import ResearchOrchestrator


@pytest.mark.parametrize(
    "risk_result",
    ({}, {"status": "PASSED"}, {"passed": True}, {"passed": True, "max_drawdown": 0.08}),
)
def test_workflow_does_not_turn_unstructured_risk_mapping_into_eligible_decision(risk_result: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="structured|paper decision"):
        ResearchOrchestrator().make_paper_decision(
            RiskReview(status="PASSED"),
            (AgentReport("technical", "READY", evidence_refs=("artifact:technical",)),),
            {},
            "AAA",
            risk_result=risk_result,
        )
