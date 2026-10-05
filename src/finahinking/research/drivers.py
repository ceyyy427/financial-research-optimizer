"""Model-driver boundaries for offline, Codex, and explicit user providers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from .contracts import (
    AgentReport,
    FailureKind,
    ResearchPlan,
    ResearchRequest,
    stable_digest,
)
from .providers import ModelEnvelope, ProviderAdapter


@dataclass(frozen=True, slots=True)
class CodexPlanEnvelope:
    request_id: str
    role_names: tuple[str, ...]
    input_digest: str
    context_digest: str
    prompt_digest: str
    instructions: str = "Review this handoff and return structured research findings."

    def __post_init__(self) -> None:
        if not self.request_id.strip() or not self.input_digest.strip() or not self.context_digest.strip():
            raise ValueError("Codex handoff identity fields must be non-empty")
        object.__setattr__(self, "role_names", tuple(sorted(set(self.role_names))))
        object.__setattr__(self, "instructions", self.instructions.strip())

    @property
    def tool_names(self) -> tuple[str, ...]:
        """Codex handoff never authorizes direct tool execution."""

        return ()


@dataclass(frozen=True, slots=True)
class DriverResult:
    reports: tuple[AgentReport, ...] = ()
    research_plan: ResearchPlan | None = None
    failure_kind: FailureKind | None = None
    failure_message: str | None = None
    requires_external_turn: bool = False
    envelope: CodexPlanEnvelope | None = None


class ModelDriver(Protocol):
    def propose(self, request: ResearchRequest, context: Mapping[str, Any]) -> DriverResult: ...


class OfflineDriver:
    def propose(self, request: ResearchRequest, context: Mapping[str, Any]) -> DriverResult:
        plan = request.research_plan if isinstance(request.research_plan, ResearchPlan) else ResearchPlan(hypotheses=(request.research_plan,))
        fixture_digest = stable_digest({"request": request, "context": context})
        reports = tuple(
            AgentReport(
                role=role,
                status="OFFLINE",
                claims=(f"offline fixture observation {fixture_digest[:12]}",),
                evidence_refs=(f"artifact:offline:{role}",),
                limitations=("offline fixture; not a live market feed",),
                model_ref="offline/fixture-v1",
            )
            for role in request.analyst_roles
        )
        return DriverResult(reports=reports, research_plan=plan)


class CodexInteractiveDriver:
    def propose(self, request: ResearchRequest, context: Mapping[str, Any]) -> DriverResult:
        input_digest = stable_digest(request)
        context_digest = stable_digest(context)
        envelope = CodexPlanEnvelope(
            request_id=request.run_id,
            role_names=request.analyst_roles,
            input_digest=input_digest,
            context_digest=context_digest,
            prompt_digest=stable_digest({"input": input_digest, "context": context_digest}),
        )
        return DriverResult(
            research_plan=request.research_plan if isinstance(request.research_plan, ResearchPlan) else None,
            requires_external_turn=True,
            envelope=envelope,
        )


class UserApiDriver:
    def __init__(self, selection: Any, adapter: ProviderAdapter | None) -> None:
        self.selection = selection
        self.adapter = adapter

    def propose(self, request: ResearchRequest, context: Mapping[str, Any]) -> DriverResult:
        if self.adapter is None:
            return DriverResult(
                failure_kind=FailureKind.PROVIDER_NOT_CONFIGURED,
                failure_message="explicit provider adapter is required",
            )
        role = request.analyst_roles[0] if request.analyst_roles else "research"
        envelope = ModelEnvelope(
            request_id=request.run_id,
            role=role,
            input_digest=stable_digest(request),
            context_digest=stable_digest(context),
        )
        response = self.adapter.invoke(envelope)
        try:
            report = AgentReport(
                role=role,
                status=str(response.content.get("status", "READY")),
                claims=tuple(str(item) for item in response.content.get("claims", ())),
                evidence_refs=tuple(str(item) for item in response.content.get("evidence_refs", ())),
                limitations=tuple(str(item) for item in response.content.get("limitations", ())),
                model_ref=f"{response.provider}/{response.model}",
            )
        except (TypeError, ValueError) as exc:
            return DriverResult(
                failure_kind=FailureKind.VALIDATION_FAILED,
                failure_message=f"provider response schema invalid: {exc}",
            )
        plan = request.research_plan if isinstance(request.research_plan, ResearchPlan) else None
        return DriverResult(reports=(report,), research_plan=plan)


class CompatibleApiDriver(UserApiDriver):
    def __init__(self) -> None:
        super().__init__(selection=None, adapter=None)
