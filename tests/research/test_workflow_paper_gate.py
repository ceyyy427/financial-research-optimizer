from __future__ import annotations

import pytest

from finahinking.research.contracts import AgentReport, RiskReview
from finahinking.research.workflow import ResearchOrchestrator


def test_workflow_does_not_turn_unstructured_passed_mapping_into_eligible_decision() -> None:
    with pytest.raises(ValueError, match="structured|paper decision"):
        ResearchOrchestrator().make_paper_decision(
            RiskReview(status="PASSED"),
            (AgentReport("technical", "READY", evidence_refs=("artifact:technical",)),),
            {},
            "AAA",
            risk_result={"passed": True},
        )
