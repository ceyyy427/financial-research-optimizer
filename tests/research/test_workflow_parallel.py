from __future__ import annotations

import threading
import time
from concurrent.futures import CancelledError
from datetime import date

from finahinking.quant.services import QuantServiceGateway
from finahinking.research.analyst_runtime import AnalystPool, ResearchManager
from finahinking.research.contracts import (
    AgentReport,
    FailureKind,
    ResearchPlan,
    ResearchRequest,
    ResearchState,
)
from finahinking.research.drivers import DriverResult, OfflineDriver
from finahinking.research.tools import ResearchToolGateway
from finahinking.research.workflow import AnalystSpec, ResearchOrchestrator, WorkflowLimits


def make_request(roles: tuple[str, ...] = ("fundamentals", "technical", "learning")) -> ResearchRequest:
    return ResearchRequest(
        run_id="run-parallel",
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(
            hypotheses=("trend",),
            required_datasets=("fixture-prices",),
            factor_ids=("fixture.factor.v1",),
        ),
        analyst_roles=roles,
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg-parallel",
    )


def quant_tools(*, quant: bool = True, risk: bool = True) -> ResearchToolGateway:
    gateway = QuantServiceGateway()
    if quant:
        gateway.register("quant.run_backtest", lambda params: {"annual_return": 0.1, "oos": True})
    if risk:
        gateway.register("quant.analyze_risk", lambda params: {"passed": True, "max_drawdown": 0.08})
    return ResearchToolGateway(quant_gateway=gateway)


class ParallelDriver:
    def __init__(self, *, missing: set[str] | None = None, provider_failure: bool = False) -> None:
        self.missing = missing or set()
        self.provider_failure = provider_failure
        self.lock = threading.Lock()
        self.started: set[str] = set()
        self.finished: set[str] = set()

    def propose(self, request: ResearchRequest, context: dict[str, object]) -> DriverResult:
        role = str(context["analyst_role"])
        with self.lock:
            self.started.add(role)
        time.sleep(0.01 if role != "fundamentals" else 0.03)
        with self.lock:
            self.finished.add(role)
        if self.provider_failure:
            return DriverResult(failure_kind=FailureKind.PROVIDER_NOT_CONFIGURED, failure_message="provider unavailable")
        if role in self.missing:
            return DriverResult()
        return DriverResult(
            reports=(
                AgentReport(
                    role=role,
                    status="READY",
                    claims=(f"observation:{role}",),
                    evidence_refs=(f"artifact:{role}",),
                    model_ref="fixture/model-v1",
                ),
            )
        )


class RecordingManager(ResearchManager):
    def __init__(self, driver: ParallelDriver) -> None:
        self.driver = driver
        self.called_after_roles: tuple[str, ...] | None = None

    def synthesize(self, reports, request):
        self.called_after_roles = tuple(sorted(self.driver.finished))
        return super().synthesize(reports, request)


class RecordingPool(AnalystPool):
    def __init__(self) -> None:
        self.max_workers_seen: int | None = None

    def run(self, specs, request, driver, context, max_workers=5):
        self.max_workers_seen = max_workers
        return super().run(specs, request, driver, context, max_workers=max_workers)


class CancelledPool:
    def run(self, specs, request, driver, context, max_workers=5):
        raise CancelledError()


class ExplodingDriver:
    def propose(self, request, context):
        raise RuntimeError("api_key=super-secret https://evil.test /Users/private prompt=hidden raw provider response")


class ExplodingPool:
    def run(self, specs, request, driver, context, max_workers=5):
        raise RuntimeError("api_key=super-secret https://evil.test /Users/private prompt=hidden raw provider response")


class FailedDriver:
    def propose(self, request, context):
        return DriverResult(
            failure_kind=FailureKind.INTERNAL_ERROR,
            failure_message="api_key=super-secret https://evil.test /Users/private prompt=hidden raw provider response",
        )


def test_parallel_pool_completes_before_manager_and_preserves_stage_order() -> None:
    driver = ParallelDriver()
    manager = RecordingManager(driver)
    specs = (
        AnalystSpec("fundamentals"),
        AnalystSpec("technical"),
        AnalystSpec("learning", required=False),
    )

    result = ResearchOrchestrator().run(
        make_request(),
        driver,
        quant_tools(),
        analyst_specs=specs,
        analyst_pool=AnalystPool(),
        manager=manager,
    )

    assert set(manager.called_after_roles or ()) == {"fundamentals", "technical", "learning"}
    assert result.state.state_history.index(ResearchState.ANALYSTS_READY) < result.state.state_history.index(ResearchState.EVIDENCE_REVIEW)
    assert result.state.current_state is ResearchState.LEARNING_RECORDED
    assert result.decision is not None
    assert [report.role for report in result.state.analyst_reports] == ["fundamentals", "technical", "learning"]
    ready_event = next(event for event in result.events if event.state is ResearchState.ANALYSTS_READY)
    assert ready_event.actor == "analyst_pool"
    assert ready_event.metadata["stage_owner"] == "analyst_pool"
    assert ready_event.metadata["provider_models"] == (
        ("fundamentals", "fixture/model-v1"),
        ("technical", "fixture/model-v1"),
        ("learning", "fixture/model-v1"),
    )


def test_required_role_failure_stops_before_evidence_review_with_typed_state() -> None:
    result = ResearchOrchestrator().run(
        make_request(),
        ParallelDriver(missing={"fundamentals"}),
        quant_tools(),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )

    assert result.state.current_state is ResearchState.FAILED
    assert result.state.failure_kind is FailureKind.ANALYST_REQUIRED_MISSING
    assert ResearchState.EVIDENCE_REVIEW not in result.state.state_history
    assert result.decision is None


def test_optional_role_failure_is_partial_and_keeps_decision_eligible() -> None:
    result = ResearchOrchestrator().run(
        make_request(),
        ParallelDriver(missing={"learning"}),
        quant_tools(),
        analyst_specs=(AnalystSpec("fundamentals"), AnalystSpec("technical"), AnalystSpec("learning", required=False)),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )

    assert result.state.current_state is ResearchState.LEARNING_RECORDED
    assert result.state.failure_kind is FailureKind.ANALYST_OPTIONAL_FAILURE
    assert result.state.decision_eligible is True
    assert result.decision is not None
    assert "partial_analysis" in (result.state.failure_message or "")


def test_provider_not_configured_from_parallel_role_is_terminal_and_redacted() -> None:
    result = ResearchOrchestrator().run(
        make_request(),
        ParallelDriver(provider_failure=True),
        quant_tools(),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )

    assert result.state.current_state is ResearchState.PROVIDER_NOT_CONFIGURED
    assert result.state.failure_kind is FailureKind.PROVIDER_NOT_CONFIGURED
    assert result.decision is None
    assert all("prompt" not in repr(event).lower() for event in result.events)
    assert all("secret" not in repr(event).lower() for event in result.events)


def test_core_quant_and_risk_failures_block_decision_after_parallel_stage() -> None:
    quant_failed = ResearchOrchestrator().run(
        make_request(),
        OfflineDriver(),
        quant_tools(quant=False),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )
    assert quant_failed.state.current_state is ResearchState.VALIDATION_FAILED
    assert quant_failed.state.failure_kind is FailureKind.QUANT_VALIDATION_FAILED
    assert quant_failed.decision is None

    risk_failed = ResearchOrchestrator().run(
        make_request(),
        OfflineDriver(),
        quant_tools(risk=False),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )
    assert risk_failed.state.current_state is ResearchState.VALIDATION_FAILED
    assert risk_failed.state.failure_kind is FailureKind.RISK_REVIEW_FAILED
    assert risk_failed.decision is None


def test_parallel_max_workers_is_bounded_by_workflow_limits() -> None:
    pool = RecordingPool()
    result = ResearchOrchestrator().run(
        make_request(("fundamentals", "technical", "sentiment")),
        OfflineDriver(),
        quant_tools(),
        analyst_pool=pool,
        manager=ResearchManager(),
        limits=WorkflowLimits(max_analyst_workers=1),
    )
    assert result.state.current_state is ResearchState.LEARNING_RECORDED
    assert pool.max_workers_seen == 1


def test_parallel_cancellation_is_typed_and_cannot_publish_a_decision() -> None:
    result = ResearchOrchestrator().run(
        make_request(),
        OfflineDriver(),
        quant_tools(),
        analyst_pool=CancelledPool(),
        manager=ResearchManager(),
    )
    assert result.state.current_state is ResearchState.CANCELLED
    assert result.state.failure_kind is FailureKind.CANCELLED
    assert result.decision is None


def test_parallel_exception_is_generic_and_blocks_decision() -> None:
    result = ResearchOrchestrator().run(
        make_request(),
        OfflineDriver(),
        quant_tools(),
        analyst_pool=ExplodingPool(),
        manager=ResearchManager(),
    )
    assert result.state.current_state is ResearchState.FAILED
    assert result.state.failure_kind is FailureKind.INTERNAL_ERROR
    assert result.state.failure_message == "analyst pool failed"
    assert result.decision is None
    encoded = repr(result)
    assert all(value not in encoded for value in ("super-secret", "evil.test", "/Users/private", "prompt=hidden", "raw provider response"))


def test_non_parallel_driver_exception_is_generic_and_blocks_decision() -> None:
    result = ResearchOrchestrator().run(make_request(("fundamentals",)), ExplodingDriver(), quant_tools())
    assert result.state.current_state is ResearchState.FAILED
    assert result.state.failure_kind is FailureKind.INTERNAL_ERROR
    assert result.state.failure_message == "driver failed"
    assert result.decision is None
    encoded = repr(result)
    assert all(value not in encoded for value in ("super-secret", "evil.test", "/Users/private", "prompt=hidden", "raw provider response"))


def test_non_parallel_driver_failure_message_is_not_published() -> None:
    result = ResearchOrchestrator().run(make_request(("fundamentals",)), FailedDriver(), quant_tools())
    assert result.state.failure_message == "driver failed"
    assert result.decision is None
    encoded = repr(result)
    assert all(value not in encoded for value in ("super-secret", "evil.test", "/Users/private", "prompt=hidden", "raw provider response"))
