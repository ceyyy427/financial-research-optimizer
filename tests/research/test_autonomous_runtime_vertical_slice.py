from __future__ import annotations

import json
import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd
import pytest

from finahinking.data.connection_settings import (
    InMemoryDataCredentialStore,
    PersistentDataConnectionStore,
)
from finahinking.data.user_api import JsonApiConnector, TransportResponse
from finahinking.data.user_api_contracts import DataConnectionConfig, DataRequest
from finahinking.quant.services import QuantServiceGateway
from finahinking.research.analyst_runtime import AnalystPool, ResearchManager
from finahinking.research.codex_bridge import CodexBridge
from finahinking.research.contracts import (
    AgentReport,
    AgentTask,
    CheckpointIdentity,
    FailureKind,
    ResearchPlan,
    ResearchRequest,
    stable_digest,
)
from finahinking.research.drivers import DriverResult, ModelDriver
from finahinking.research.factor_pipeline import FactorResearchPipeline
from finahinking.research.factor_proposals import FactorHypothesis
from finahinking.research.job_queue import JobQueue, JobStatus
from finahinking.research.learning_manager import LearningManager, LearningUpdateStatus
from finahinking.research.paper_trader import PaperTrader
from finahinking.research.portfolio_runtime import PortfolioManager
from finahinking.research.provider_adapters import (
    OpenAICompatibleAdapter,
    ProviderAdapterError,
    ProviderFailureKind,
)
from finahinking.research.providers import ModelEnvelope
from finahinking.research.reports import ReportBundleWriter, verify_report_bundle
from finahinking.research.risk_runtime import RiskManager
from finahinking.research.run_store import ResearchRunStore
from finahinking.research.settlement import SettlementEvent
from finahinking.research.tools import ResearchToolGateway, ResearchToolResponse, ResearchToolStatus
from finahinking.research.worker import ResearchWorker, WorkerStatus
from finahinking.research.workflow import AnalystSpec, ResearchOrchestrator


class _MockTransport:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def request(self, url: str, *, headers: dict[str, str], timeout: float, allow_redirects: bool = False) -> TransportResponse:
        del url, headers, timeout, allow_redirects
        return TransportResponse(200, {"content-type": "application/json"}, json.dumps(self.payload).encode(), "https://example.com/api")


class _OfflineFiveRoleDriver(ModelDriver):
    def propose(self, request: ResearchRequest, context: dict[str, object]) -> DriverResult:
        assert isinstance(context.get("dataset"), dict)
        return DriverResult(
            reports=tuple(
                AgentReport(
                    role=role,
                    status="READY",
                    claims=(f"offline observation {role}",),
                    evidence_refs=(f"artifact:fixture:{role}",),
                    limitations=("offline fixture",),
                    model_ref="offline/fixture-v1",
                )
                for role in request.analyst_roles
            )
        )


class _FixtureTools(ResearchToolGateway):
    def __init__(self) -> None:
        quant = QuantServiceGateway()
        quant.register("quant.run_backtest", lambda params: {"passed": True, "oos": True, "engine": "deterministic"})
        quant.register(
            "quant.analyze_risk",
            lambda params: {"passed": True, "max_drawdown": 0.1},
        )
        super().__init__(quant_gateway=quant)

    def execute(self, request):
        response = super().execute(request)
        if request.name == "research.inspect_dataset" and response.result is not None:
            return response.__class__(
                request_id=response.request_id,
                name=response.name,
                status=response.status,
                result={**dict(response.result), "pit_available": "AVAILABLE"},
                failure_kind=response.failure_kind,
                provenance=response.provenance,
                request_digest=response.request_digest,
            )
        return response


def _config() -> DataConnectionConfig:
    return DataConnectionConfig(
        "fixture-feed",
        "Fixture feed",
        "https://example.com/api",
        None,
        "no_auth",
        {"instrument": "ticker", "timestamp": "time", "available_at": "available", "close": "price", "volume": "qty"},
        "data",
    )


def _payload() -> dict[str, object]:
    return {
        "data": [
            {"ticker": "AAA", "time": f"2026-09-{day:02d}", "available": f"2026-09-{day:02d}", "price": str(100 + ((day * 7) % 11)), "qty": str(100 + day)}
            for day in range(1, 30)
        ]
    }


def _request(run_id: str = "autonomous-release") -> ResearchRequest:
    return ResearchRequest(
        run_id=run_id,
        instrument="AAA",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(hypotheses=("bounded momentum",), required_datasets=("prices",), factor_ids=("fixture.factor.v1",)),
        analyst_roles=("fundamentals", "technical", "sentiment", "news", "learning"),
        asset_class="EQUITY",
        workflow_version="research.v1",
        config_digest="release-fixture-v1",
    )


def _batch():
    connector = JsonApiConnector(_config(), InMemoryDataCredentialStore(), _MockTransport(_payload()), resolver=lambda host, port=None: ("93.184.216.34",))
    return connector.fetch(DataRequest("prices", ("AAA",), "2026-09-01", "2026-09-29", "2026-10-01"))


def _factor_result(batch):
    index = pd.DatetimeIndex([record["timestamp"] for record in batch.records])
    close = pd.Series([record["close"] for record in batch.records], index=index, dtype=float)
    volume = pd.Series([record["volume"] for record in batch.records], index=index, dtype=float)
    dataset = {"frame": pd.DataFrame({"close": close, "volume": volume}), "forward_return": close.pct_change().shift(-1)}
    return FactorResearchPipeline().run(
        FactorHypothesis("release-momentum", "bounded momentum", "momentum", ("close",), 2, "positive"),
        dataset,
        {"source_ids": ("fixture-source",), "license_status": "fixture", "pit_semantics": "POINT_IN_TIME", "min_samples": 8},
    ), dataset


def _assert_public_tree(root: Path) -> None:
    forbidden = ("api_key", "secret", "endpoint", "prompt", "raw_provider")
    active_execution = re.compile(r"(?:placed|submitted|executed|filled)\s+(?:an?\s+)?order|broker\s+(?:api|gateway)|live\s+(?:endpoint|trading)", re.IGNORECASE)
    absolute = re.compile(r"(?:/(?:Users|home|private|tmp|var|etc|opt)/|[A-Za-z]:[\\/])")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.casefold()
        assert not any(marker in lowered for marker in forbidden), path
        assert not active_execution.search(text), path
        assert not absolute.search(text), path
        if path.suffix == ".html":
            HTMLParser(convert_charrefs=True).feed(text)


def test_autonomous_runtime_vertical_slice_is_recoverable_and_public(tmp_path: Path) -> None:
    store = PersistentDataConnectionStore(tmp_path / "connections.json", credential_store=InMemoryDataCredentialStore())
    store.save(_config())
    reopened = PersistentDataConnectionStore(tmp_path / "connections.json", credential_store=InMemoryDataCredentialStore())
    batch = _batch()
    tools = _FixtureTools()
    result = ResearchOrchestrator(
        connection_store=reopened,
        data_transport=_MockTransport(_payload()),
        data_resolver=lambda host, port=None: ("93.184.216.34",),
    ).run_from_connection(
        "fixture-feed",
        _request(),
        driver=_OfflineFiveRoleDriver(),
        tools=tools,
        analyst_specs=tuple(AnalystSpec(role) for role in _request().analyst_roles),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )
    assert result.state.current_state.value == "LEARNING_RECORDED"
    assert result.state.decision_eligible is True

    factor_result, _dataset = _factor_result(batch)
    assert factor_result.research_run.rounds
    snapshot = {"pit_status": "AVAILABLE", "as_of": "2026-10-01", "observations": [dict(item) for item in batch.records], "stress_results": {"base": {"passed": True}}}
    factor_payload = {"status": "PASSED", "metrics": {"liquidity": 100.0, "drawdown": 0.1}, "passed": True}
    constraints = {"min_liquidity": 1.0, "max_concentration": 1.0, "max_drawdown": 0.5, "stress_scenarios": {"base": {"drawdown": 0.1}}, "long_only": True, "max_exposure": 0.8, "max_single_weight": 0.8}
    risk = RiskManager().review(snapshot, factor_payload, constraints)
    assert risk.passed is True
    portfolio = PortfolioManager().construct(risk, ("AAA",), constraints)
    ledger = PaperTrader().simulate(portfolio, snapshot, {"initial_cash": 1.0, "fee_bps": 5.0, "slippage_bps": 2.0})
    settlement = SettlementEvent("autonomous-release", ledger, date(2026, 10, 1), {"factor_weight_updates": {"release": 0.1}}, {}, ledger.snapshot_digest)
    proposal = LearningManager().propose_update(settlement)
    assert proposal.status is LearningUpdateStatus.PROPOSAL_READY

    report_root = tmp_path / "reports"
    ReportBundleWriter().write(result, report_root)
    assert verify_report_bundle(report_root / "autonomous-release" / "manifest.json").ok
    _assert_public_tree(report_root)

    identity = CheckpointIdentity("AAA", date(2026, 10, 1), {"id": "fixture", "as_of": "2026-10-01", "digest": batch.data_fingerprint}, _request().analyst_roles, {role: "offline/fixture-v1" for role in _request().analyst_roles}, {"workflow": "research.v1"}, "research.v1", 1, 1, "release-fixture-v1", stable_digest(_request().research_plan))
    checkpoint = ResearchRunStore(tmp_path / "checkpoints", workflow_version="research.v1")
    checkpoint.save_checkpoint(result.state.__class__(result.state.run_id, result.state.current_state.__class__("QUANT_VALIDATION"), result.state.as_of, result.state.state_history[:8], result.state.analyst_reports), identity)
    assert checkpoint.load_checkpoint("autonomous-release", identity).current_state.value == "QUANT_VALIDATION"


def test_connection_entrypoint_keeps_default_target_validation_fail_closed(tmp_path: Path) -> None:
    store = PersistentDataConnectionStore(tmp_path / "connections.json", credential_store=InMemoryDataCredentialStore())
    store.save(_config())
    result = ResearchOrchestrator(connection_store=store, data_transport=_MockTransport(_payload())).run_from_connection(
        "fixture-feed",
        _request("default-resolver-blocked"),
    )
    assert result.state.current_state.value == "DATA_UNAVAILABLE"
    assert result.state.failure_kind is FailureKind.DATA_UNAVAILABLE


def test_provider_codex_offline_and_queue_recovery(tmp_path: Path) -> None:
    envelope = ModelEnvelope("release-provider", "technical", "input-digest", "context-digest")
    with_adapter = OpenAICompatibleAdapter(model="fixture-v1", endpoint="https://provider.example.test/v1", transport=lambda *args, **kwargs: {"status": 200, "json": {"schema_version": "research-model.v1", "content": {"status": "READY", "claims": ["offline"]}, "finish_reason": "stop"}})
    assert with_adapter.invoke(envelope).content["status"] == "READY"
    try:
        OpenAICompatibleAdapter(model="fixture-v1").invoke(envelope)
    except ProviderAdapterError as exc:
        assert exc.kind is ProviderFailureKind.NOT_CONFIGURED
    else:
        raise AssertionError("unconfigured provider must fail closed")
    task = AgentTask("technical", "release-task", "release-input", ("paper_only",), inputs={"scope": "fixture"})
    handoff = CodexBridge().create_handoff(task)
    assert CodexBridge().accept_result(handoff, None).status == "EXTERNAL_HANDOFF_REQUIRED"

    queue = JobQueue(tmp_path / "jobs.sqlite", backoff_base_seconds=0, max_attempts=2)
    job = queue.enqueue(task, "release-idempotency")
    claimed = queue.claim("release-worker")
    assert claimed is not None and claimed.job_id == job.job_id
    retried = queue.retry(job.job_id, "fixture retry", worker_id="release-worker", attempt=claimed.attempts, lease_until=claimed.lease_until, lease_token=claimed.lease_token)
    assert retried.status is JobStatus.RETRYABLE
    claimed_again = queue.claim("release-worker")
    assert claimed_again is not None and claimed_again.attempts == 2
    cancelled = queue.cancel(job.job_id)
    assert cancelled.cancel_requested is True
    cancelled = queue.retry(job.job_id, "cancelled", worker_id="release-worker", attempt=claimed_again.attempts, lease_until=claimed_again.lease_until, lease_token=claimed_again.lease_token)
    assert cancelled.status is JobStatus.CANCELLED
    reopened = JobQueue(tmp_path / "jobs.sqlite", backoff_base_seconds=0, max_attempts=2)
    assert reopened.get(job.job_id).status is JobStatus.CANCELLED


@pytest.mark.parametrize("stage", ("data", "provider", "quant"))
def test_required_stage_failure_is_fail_closed(stage: str, tmp_path: Path) -> None:
    request = _request(f"release-failure-{stage}")
    if stage == "data":
        missing = ResearchOrchestrator(connection_store=PersistentDataConnectionStore(tmp_path / "missing.json", credential_store=InMemoryDataCredentialStore()))
        result = missing.run_from_connection("missing", request)
    else:
        class _FailingTools(_FixtureTools):
            def execute(self, tool_request):
                if stage == "quant" and tool_request.name == "quant.run_backtest":
                    return ResearchToolResponse(tool_request.run_id, tool_request.name, ResearchToolStatus.FAILED, failure_kind=FailureKind.QUANT_VALIDATION_FAILED, provenance={"fixture": "failure"}, request_digest=tool_request.request_digest)
                return super().execute(tool_request)

        class _FailingProvider(_OfflineFiveRoleDriver):
            def propose(self, request, context):
                del request, context
                return DriverResult(failure_kind=FailureKind.PROVIDER_NOT_CONFIGURED)

        driver = _FailingProvider() if stage == "provider" else _OfflineFiveRoleDriver()
        result = ResearchOrchestrator(connection_store=PersistentDataConnectionStore(tmp_path / "connections.json", credential_store=InMemoryDataCredentialStore()), data_transport=_MockTransport(_payload())).run_from_connection(
            "missing", request, driver=driver, tools=_FailingTools(), analyst_specs=tuple(AnalystSpec(role) for role in request.analyst_roles), analyst_pool=AnalystPool(), manager=ResearchManager()
        )
    assert result.decision is None
    assert result.state.decision_eligible is False


def test_factor_risk_portfolio_and_worker_fail_closed(tmp_path: Path) -> None:
    batch = _batch()
    index = pd.DatetimeIndex([record["timestamp"] for record in batch.records])
    close = pd.Series([record["close"] for record in batch.records], index=index, dtype=float)
    with pytest.raises(ValueError, match="future-looking"):
        FactorResearchPipeline().run(
            FactorHypothesis("release-invalid", "invalid", "momentum", ("close",), 2, "positive"),
            {"frame": pd.DataFrame({"close": close, "future_return": close}), "forward_return": close.pct_change().shift(-1)},
        )
    blocked = RiskManager().review({"pit_status": "UNKNOWN"}, {"status": "PASSED", "metrics": {"drawdown": 0.1}}, {"max_drawdown": 0.5, "stress_scenarios": {"base": {"drawdown": 0.1}}})
    assert blocked.passed is False
    portfolio = PortfolioManager().construct(blocked, ("AAA",), {"long_only": True})
    assert portfolio.passed is False
    with pytest.raises(ValueError, match="passed portfolio"):
        PaperTrader().simulate(portfolio, {"pit_status": "AVAILABLE", "records": []}, {})
    task = AgentTask("technical", "failure-worker", "failure-input", ("paper_only",), inputs={"scope": "fixture"})
    queue = JobQueue(tmp_path / "failed.sqlite", backoff_base_seconds=0, max_attempts=1)
    queue.enqueue(task, "failure-worker-key")
    worker = ResearchWorker(queue, worker_id="failure-worker", runner=lambda task, checkpoint: {"status": "completed", "result_ref": "../secret"})
    outcome = worker.run_once()
    assert outcome.status is WorkerStatus.FAILED
    assert queue.get(outcome.job_id).status is JobStatus.FAILED
