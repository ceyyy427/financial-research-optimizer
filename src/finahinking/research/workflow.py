"""Bounded, paper-only research workflow orchestration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .contracts import (
    AgentReport,
    DecisionCard,
    FailureKind,
    ResearchPlan,
    ResearchRequest,
    ResearchRunResult,
    ResearchRunState,
    ResearchState,
    RiskReview,
    RunEvent,
    stable_digest,
    validate_transition,
)
from .drivers import ModelDriver, OfflineDriver
from .tools import ResearchToolGateway, ResearchToolRequest, ResearchToolStatus


@dataclass(frozen=True, slots=True)
class AnalystSpec:
    role: str
    required: bool = True
    max_rounds: int = 1
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.role.strip():
            raise ValueError("analyst role must be non-empty")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be positive")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True, slots=True)
class WorkflowLimits:
    max_analyst_rounds: int = 2
    max_tool_rounds: int = 8
    max_risk_rounds: int = 2

    def __post_init__(self) -> None:
        if min(self.max_analyst_rounds, self.max_tool_rounds, self.max_risk_rounds) < 1:
            raise ValueError("workflow limits must be positive")


DEFAULT_ROLES = ("fundamentals", "technical", "sentiment", "news", "learning")


def _default_specs(request: ResearchRequest) -> tuple[AnalystSpec, ...]:
    roles = request.analyst_roles or DEFAULT_ROLES
    return tuple(AnalystSpec(role=role, required=role != "learning") for role in roles)


def _paper_claim(claim: str) -> str:
    lowered = claim.casefold()
    if any(term in lowered for term in ("executed", "filled order", "placed order", "bought", "sold")):
        return "paper-only research observation; model execution claim ignored"
    return claim


def _sanitize_report(report: AgentReport) -> AgentReport:
    return AgentReport(
        role=report.role,
        status=report.status,
        claims=tuple(_paper_claim(claim) for claim in report.claims),
        evidence_refs=report.evidence_refs,
        limitations=report.limitations,
        model_ref=report.model_ref,
        finished_at=report.finished_at,
    )


class ResearchOrchestrator:
    def run(
        self,
        request: ResearchRequest,
        driver: ModelDriver,
        tools: ResearchToolGateway,
        provider_registry: Any | None = None,
        analyst_specs: Sequence[AnalystSpec] | None = None,
        limits: WorkflowLimits | None = None,
    ) -> ResearchRunResult:
        del provider_registry  # Provider checks happen at the driver boundary.
        limits = limits or WorkflowLimits()
        specs = tuple(analyst_specs or _default_specs(request))
        state_history: list[ResearchState] = [ResearchState.RECEIVED]
        events: list[RunEvent] = [self._event(request.run_id, ResearchState.RECEIVED, "workflow", {"step": 0})]
        reports: tuple[AgentReport, ...] = ()
        failure_message: str | None = None

        def transition(next_state: ResearchState, payload: Mapping[str, Any]) -> None:
            validate_transition(state_history[-1], next_state)
            state_history.append(next_state)
            events.append(self._event(request.run_id, next_state, "workflow", payload))

        def finish(next_state: ResearchState, kind: FailureKind, message: str) -> ResearchRunResult:
            transition(next_state, {"failure_kind": kind.value, "message_digest": stable_digest(message)})
            state = ResearchRunState(
                run_id=request.run_id,
                current_state=next_state,
                as_of=request.as_of,
                state_history=tuple(state_history),
                analyst_reports=reports,
                failure_kind=kind,
                failure_message=message,
                decision_eligible=False,
            )
            return ResearchRunResult(state=state, events=tuple(events))

        transition(ResearchState.IDENTIFIED, {"instrument": request.instrument})
        dataset_id = request.research_plan.required_datasets[0] if isinstance(request.research_plan, ResearchPlan) and request.research_plan.required_datasets else "fixture"
        data_response = tools.execute(
            ResearchToolRequest(
                name="research.inspect_dataset",
                args={"dataset_id": dataset_id, "as_of": request.as_of.isoformat()},
                run_id=request.run_id,
            )
        )
        if data_response.status is not ResearchToolStatus.SUCCEEDED:
            kind = data_response.failure_kind or FailureKind.DATA_UNAVAILABLE
            target = ResearchState.NO_DATA_AVAILABLE if kind is FailureKind.NO_DATA_AVAILABLE else ResearchState.DATA_UNAVAILABLE
            transition(ResearchState.DATA_CHECKED, {"dataset_status": kind.value})
            return finish(target, kind, f"dataset check failed: {kind.value}")
        transition(ResearchState.DATA_CHECKED, {"dataset_digest": stable_digest(data_response.result)})
        transition(ResearchState.ANALYSTS_RUNNING, {"roles": tuple(sorted(spec.role for spec in specs))})

        driver_result = driver.propose(request, {"dataset": data_response.result, "max_rounds": limits.max_analyst_rounds})
        if driver_result.failure_kind is not None:
            target = ResearchState.PROVIDER_NOT_CONFIGURED if driver_result.failure_kind is FailureKind.PROVIDER_NOT_CONFIGURED else ResearchState.FAILED
            return finish(target, driver_result.failure_kind, driver_result.failure_message or "driver failed")
        if driver_result.requires_external_turn:
            return finish(ResearchState.PROVIDER_NOT_CONFIGURED, FailureKind.PROVIDER_NOT_CONFIGURED, "Codex handoff requires an explicit external turn")

        reports = tuple(sorted((_sanitize_report(report) for report in driver_result.reports), key=lambda report: report.role))
        report_by_role = {report.role: report for report in reports}
        missing_required = [spec.role for spec in specs if spec.required and spec.role not in report_by_role]
        failed_required = [spec.role for spec in specs if spec.required and report_by_role.get(spec.role, AgentReport(spec.role, "MISSING")).status == "FAILED"]
        if missing_required or failed_required:
            details = f"required analyst failure: missing={missing_required}, failed={failed_required}"
            return finish(ResearchState.FAILED, FailureKind.INTERNAL_ERROR, details)
        partial = [spec.role for spec in specs if not spec.required and spec.role not in report_by_role]
        if partial:
            failure_message = f"partial_analysis: optional roles unavailable: {', '.join(sorted(partial))}"
        transition(ResearchState.ANALYSTS_READY, {"report_roles": tuple(report_by_role)})
        transition(ResearchState.EVIDENCE_REVIEW, {"evidence_count": sum(len(report.evidence_refs) for report in reports)})
        plan = driver_result.research_plan if isinstance(driver_result.research_plan, ResearchPlan) else self.review_evidence(reports, tools)
        if not all(report.evidence_refs for report in reports if report.status != "FAILED"):
            return finish(ResearchState.VALIDATION_FAILED, FailureKind.VALIDATION_FAILED, "every usable analyst report needs evidence refs")
        transition(ResearchState.RESEARCH_PLAN_READY, {"plan_digest": stable_digest(plan)})

        quant_response = tools.execute(
            ResearchToolRequest(
                name="quant.run_backtest",
                args={"instrument": request.instrument, "as_of": request.as_of.isoformat(), "factor_ids": plan.factor_ids},
                run_id=request.run_id,
            )
        )
        if quant_response.status is not ResearchToolStatus.SUCCEEDED:
            return finish(ResearchState.VALIDATION_FAILED, FailureKind.VALIDATION_FAILED, "quant validation failed")
        transition(ResearchState.QUANT_VALIDATION, {"quant_digest": stable_digest(quant_response.result)})

        risk_response = tools.execute(
            ResearchToolRequest(
                name="quant.analyze_risk",
                args={"instrument": request.instrument, "as_of": request.as_of.isoformat()},
                run_id=request.run_id,
            )
        )
        if risk_response.status is not ResearchToolStatus.SUCCEEDED:
            return finish(ResearchState.VALIDATION_FAILED, FailureKind.VALIDATION_FAILED, "risk review failed")
        risk_review = self.run_risk_review(plan, risk_response.result)
        if risk_review.blocking_reasons:
            return finish(ResearchState.VALIDATION_FAILED, FailureKind.VALIDATION_FAILED, "; ".join(risk_review.blocking_reasons))
        transition(ResearchState.RISK_REVIEW, {"risk_digest": stable_digest(risk_review)})
        decision = self.make_paper_decision(risk_review, reports, quant_response.result, request.instrument)
        transition(ResearchState.PAPER_DECISION_READY, {"decision_digest": stable_digest(decision)})
        transition(ResearchState.REPORT_PUBLISHED, {"report": "pending-writer"})
        transition(ResearchState.LEARNING_RECORDED, {"learning": "pending-store"})
        state = ResearchRunState(
            run_id=request.run_id,
            current_state=ResearchState.LEARNING_RECORDED,
            as_of=request.as_of,
            state_history=tuple(state_history),
            analyst_reports=reports,
            failure_message=failure_message,
            decision_eligible=True,
        )
        return ResearchRunResult(state=state, events=tuple(events), decision=decision)

    def run_analyst(self, spec: AnalystSpec, request: ResearchRequest, context: Mapping[str, Any], driver: ModelDriver | None = None) -> AgentReport:
        if spec.max_rounds > 1:
            raise ValueError("analyst rounds are bounded to one driver proposal in this phase")
        result = (driver or OfflineDriver()).propose(request, context)
        for report in result.reports:
            if report.role == spec.role:
                return _sanitize_report(report)
        raise ValueError(f"analyst {spec.role} did not return a report")

    def review_evidence(self, reports: Sequence[AgentReport], tools: ResearchToolGateway) -> ResearchPlan:
        del tools
        evidence_refs = tuple(sorted({ref for report in reports for ref in report.evidence_refs}))
        if not evidence_refs:
            raise ValueError("evidence review requires existing evidence refs")
        return ResearchPlan(
            hypotheses=tuple(sorted({claim for report in reports for claim in report.claims})),
            validation_spec={"evidence_refs": evidence_refs, "oos": True, "t_plus_one": True},
        )

    def run_risk_review(self, plan: ResearchPlan, quant_result: Any) -> RiskReview:
        del plan
        if not isinstance(quant_result, Mapping):
            return RiskReview(status="BLOCKED", blocking_reasons=("risk result is not structured",))
        if quant_result.get("passed") is False:
            return RiskReview(status="BLOCKED", blocking_reasons=("deterministic risk gate failed",))
        return RiskReview(status="PASSED", gates=("deterministic-risk",), rationale="risk gates passed")

    def make_paper_decision(self, risk_review: RiskReview, reports: Sequence[AgentReport], quant_result: Any, instrument: str) -> DecisionCard:
        if risk_review.blocking_reasons:
            raise ValueError("cannot make decision after blocked risk review")
        return DecisionCard(
            action="PAPER-ONLY research allocation",
            weights={instrument: 1.0},
            rationale=f"paper-only synthesis from {len(reports)} analyst reports and quant result {stable_digest(quant_result)[:12]}",
            evidence_refs=tuple(sorted({ref for report in reports for ref in report.evidence_refs})),
            limitations=("not a live signal; no order execution",),
            approval_required=True,
            eligible=True,
        )

    @staticmethod
    def _event(run_id: str, state: ResearchState, actor: str, payload: Mapping[str, Any]) -> RunEvent:
        return RunEvent(
            event_id=f"{run_id}:{state.value}:{stable_digest(payload)[:12]}",
            run_id=run_id,
            state=state,
            actor=actor,
            timestamp=datetime.now(UTC),
            payload_digest=stable_digest(payload),
        )
