from __future__ import annotations

from datetime import date

from finahinking.quant.services import QuantServiceGateway
from finahinking.research.contracts import (
    AgentReport,
    FailureKind,
    ResearchPlan,
    ResearchRequest,
    ResearchState,
    stable_digest,
)
from finahinking.research.drivers import DriverResult, OfflineDriver, UserApiDriver
from finahinking.research.tools import ResearchToolGateway, ResearchToolRequest, ResearchToolStatus
from finahinking.research.workflow import AnalystSpec, ResearchOrchestrator


def make_request() -> ResearchRequest:
    return ResearchRequest(
        run_id="run-workflow",
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(
            hypotheses=("trend",),
            required_datasets=("fixture-prices",),
            factor_ids=("fixture.factor.v1",),
        ),
        analyst_roles=("fundamentals", "technical", "learning"),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg",
    )


def quant_tools(*, risk: bool = True) -> ResearchToolGateway:
    quant = QuantServiceGateway()
    quant.register("quant.run_backtest", lambda params: {"annual_return": 0.1, "oos": True})
    if risk:
        quant.register("quant.analyze_risk", lambda params: {"passed": True, "max_drawdown": 0.08})
    return ResearchToolGateway(quant_gateway=quant)


def test_happy_path_reaches_learning_recorded_without_state_jump() -> None:
    result = ResearchOrchestrator().run(make_request(), OfflineDriver(), quant_tools())

    assert result.state.current_state is ResearchState.LEARNING_RECORDED
    assert result.state.decision_eligible is True
    assert result.decision is not None
    assert result.decision.paper_only is True
    assert result.state.state_history == (
        ResearchState.RECEIVED,
        ResearchState.IDENTIFIED,
        ResearchState.DATA_CHECKED,
        ResearchState.ANALYSTS_RUNNING,
        ResearchState.ANALYSTS_READY,
        ResearchState.EVIDENCE_REVIEW,
        ResearchState.RESEARCH_PLAN_READY,
        ResearchState.QUANT_VALIDATION,
        ResearchState.RISK_REVIEW,
        ResearchState.PAPER_DECISION_READY,
        ResearchState.REPORT_PUBLISHED,
        ResearchState.LEARNING_RECORDED,
    )
    assert len(result.events) == len(result.state.state_history)


class PartialDriver:
    def propose(self, request, context) -> DriverResult:
        return DriverResult(
            research_plan=request.research_plan,
            reports=(
                AgentReport(role="fundamentals", status="READY", claims=("fundamental",), evidence_refs=("artifact:fundamental",)),
                AgentReport(role="technical", status="READY", claims=("technical",), evidence_refs=("artifact:technical",)),
            ),
        )


def test_optional_analyst_failure_is_partial_but_core_quant_failure_blocks_decision() -> None:
    specs = (
        AnalystSpec("fundamentals", required=True),
        AnalystSpec("technical", required=True),
        AnalystSpec("learning", required=False),
    )
    partial = ResearchOrchestrator().run(make_request(), PartialDriver(), quant_tools(), analyst_specs=specs)
    assert partial.state.current_state is ResearchState.LEARNING_RECORDED
    assert partial.state.decision_eligible is True
    assert "learning" not in {report.role for report in partial.state.analyst_reports}

    blocked = ResearchOrchestrator().run(make_request(), OfflineDriver(), quant_tools(risk=False), analyst_specs=specs)
    assert blocked.state.current_state is ResearchState.VALIDATION_FAILED
    assert blocked.state.decision_eligible is False
    assert blocked.decision is None


def test_provider_not_configured_is_distinct_terminal_state() -> None:
    result = ResearchOrchestrator().run(
        make_request(),
        UserApiDriver(selection=None, adapter=None),
        quant_tools(),
    )
    assert result.state.current_state is ResearchState.PROVIDER_NOT_CONFIGURED
    assert result.state.failure_kind is FailureKind.PROVIDER_NOT_CONFIGURED


class UnsafeClaimDriver:
    def propose(self, request, context) -> DriverResult:
        return DriverResult(
            research_plan=request.research_plan,
            reports=tuple(
                AgentReport(role=role, status="READY", claims=("executed buy order",), evidence_refs=(f"artifact:{role}",))
                for role in request.analyst_roles
            ),
        )


def test_model_execution_claim_is_normalized_to_paper_only_and_results_are_deterministic() -> None:
    first = ResearchOrchestrator().run(make_request(), UnsafeClaimDriver(), quant_tools())
    second = ResearchOrchestrator().run(make_request(), UnsafeClaimDriver(), quant_tools())

    assert first.decision is not None and first.decision.paper_only is True
    assert all("paper" in claim.lower() or "executed" not in claim.lower() for report in first.state.analyst_reports for claim in report.claims)
    assert stable_digest(first.decision) == stable_digest(second.decision)
    assert stable_digest(first.state.analyst_reports) == stable_digest(second.state.analyst_reports)


class NoDataTools(ResearchToolGateway):
    def execute(self, request: ResearchToolRequest):
        return type("Response", (), {
            "status": ResearchToolStatus.FAILED,
            "failure_kind": FailureKind.NO_DATA_AVAILABLE,
        })()


def test_no_data_stops_before_analysts() -> None:
    result = ResearchOrchestrator().run(make_request(), OfflineDriver(), NoDataTools())
    assert result.state.current_state is ResearchState.NO_DATA_AVAILABLE
    assert result.state.failure_kind is FailureKind.NO_DATA_AVAILABLE
