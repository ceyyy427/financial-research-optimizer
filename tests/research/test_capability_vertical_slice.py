"""Offline acceptance test for the governed research capability chain.

This test intentionally uses a user supplied mock JSON API and deterministic
fixtures.  It is the release gate for composition of Tasks 1 through 8; it
does not contact a provider, install an engine, or execute a live order.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from finahinking.data.connection_settings import InMemoryDataCredentialStore
from finahinking.data.user_api import JsonApiConnector, TransportResponse
from finahinking.data.user_api_contracts import DataConnectionConfig, DataRequest
from finahinking.factors.dsl import parse_factor_expression
from finahinking.quant.services import QuantServiceGateway
from finahinking.research.analyst_runtime import AnalystPool, ResearchManager
from finahinking.research.contracts import (
    AgentReport,
    CheckpointIdentity,
    ResearchPlan,
    ResearchRequest,
    ResearchRunState,
    ResearchState,
    stable_digest,
)
from finahinking.research.drivers import DriverResult, ModelDriver
from finahinking.research.factor_proposals import (
    FactorHypothesis,
    FactorProposalCatalog,
    validate_factor_proposal,
)
from finahinking.research.learning import LearningStore, reconcile_learning
from finahinking.research.reports import ReportBundleWriter, verify_report_bundle
from finahinking.research.run_store import ResearchRunStore
from finahinking.research.tools import ResearchToolGateway, ResearchToolRequest
from finahinking.research.workflow import AnalystSpec, ResearchOrchestrator


class _MockTransport:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def request(self, url: str, *, headers: dict[str, str], timeout: float, allow_redirects: bool = False) -> TransportResponse:
        del url, headers, timeout, allow_redirects
        return TransportResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body=json.dumps(self.payload, sort_keys=True).encode("utf-8"),
            url="https://example.test/api",
        )


class _FiveRoleDriver(ModelDriver):
    def __init__(self, expected_dataset_digest: str | None = None) -> None:
        self.expected_dataset_digest = expected_dataset_digest

    def propose(self, request: ResearchRequest, context: dict[str, object]) -> DriverResult:
        if self.expected_dataset_digest is not None:
            dataset = context["dataset"]
            assert isinstance(dataset, dict)
            assert dataset["data_fingerprint"] == self.expected_dataset_digest
        reports = tuple(
            AgentReport(
                role=role,
                status="READY",
                claims=(f"fixture observation for {role}",),
                evidence_refs=(f"artifact:fixture:{role}",),
                limitations=("offline fixture; paper-only",),
                model_ref="offline/fixture-v1",
            )
            for role in request.analyst_roles
        )
        return DriverResult(reports=reports)


def _request(run_id: str = "capability-run") -> ResearchRequest:
    return ResearchRequest(
        run_id=run_id,
        instrument="AAA",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(
            hypotheses=("momentum persists",),
            required_datasets=("mock-prices",),
            factor_ids=("fixture.factor.v1",),
        ),
        analyst_roles=("fundamentals", "technical", "sentiment", "news", "learning"),
        asset_class="EQUITY",
        workflow_version="research.v1",
        config_digest="fixture-config-v1",
    )


class _FixtureTools(ResearchToolGateway):
    def __init__(self, batch, *, risk_passes: bool = True) -> None:
        quant = QuantServiceGateway()
        quant.register("quant.run_backtest", lambda params: {"engine": "finathink-deterministic", "oos": True, "passed": True, "params": params})
        quant.register("quant.analyze_risk", lambda params: {"passed": risk_passes, "max_drawdown": 0.08, "params": params})
        super().__init__(quant_gateway=quant)
        self.batch = batch

    def execute(self, request: ResearchToolRequest):
        response = super().execute(request)
        if request.name == "research.inspect_dataset" and response.result is not None:
            return replace(response, result={
                "dataset_id": request.args.get("dataset_id", "fixture"),
                "status": "AVAILABLE",
                "data_fingerprint": self.batch.data_fingerprint,
                "record_count": len(self.batch.records),
            })
        return response


def _tools(batch, *, risk_passes: bool = True) -> ResearchToolGateway:
    return _FixtureTools(batch, risk_passes=risk_passes)


def _fetch_batch():
    config = DataConnectionConfig(
        "mock-feed", "Mock fixture feed", "https://example.test/api", None, "no_auth",
        {"instrument": "ticker", "timestamp": "time", "available_at": "available", "close": "price", "volume": "qty"},
        "data",
    )
    payload = {"data": [
        {"ticker": "AAA", "time": "2026-09-29", "available": "2026-09-29", "price": "10", "qty": "100"},
        {"ticker": "AAA", "time": "2026-09-30", "available": "2026-09-30", "price": "10.5", "qty": "120"},
        {"ticker": "AAA", "time": "2026-10-01", "available": "2026-10-01", "price": "11", "qty": "110"},
    ]}
    connector = JsonApiConnector(config, InMemoryDataCredentialStore(), _MockTransport(payload), resolver=lambda host, port=None: ("93.184.216.34",))
    return connector.fetch(DataRequest("prices", ("AAA",), "2026-09-29", "2026-10-01", "2026-10-01"))


def test_offline_capability_vertical_slice_is_reproducible_and_recoverable(tmp_path: Path) -> None:
    first_batch, second_batch = _fetch_batch(), _fetch_batch()
    assert first_batch.data_fingerprint == second_batch.data_fingerprint
    assert first_batch.pit_available == "AVAILABLE"

    hypothesis = FactorHypothesis("momentum-fixture", "price momentum", "momentum", ("close",), 2, "positive")
    proposals = FactorProposalCatalog().propose(hypothesis, limit=2)
    assert proposals
    validate_factor_proposal(proposals[0])
    assert parse_factor_expression(proposals[0].expression, proposals[0].required_fields).fields

    request = _request()
    tools = _tools(first_batch)
    result = ResearchOrchestrator().run(
        request,
        _FiveRoleDriver(first_batch.data_fingerprint),
        tools,
        analyst_specs=tuple(AnalystSpec(role, required=True) for role in request.analyst_roles),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )
    assert result.state.current_state is ResearchState.LEARNING_RECORDED
    assert result.state.decision_eligible is True
    assert result.decision is not None and result.decision.approval_required is True
    assert result.decision.eligible is True
    assert tuple(report.role for report in result.state.analyst_reports) == request.analyst_roles

    bundle_root = tmp_path / "reports"
    manifest = ReportBundleWriter().write(result, bundle_root)
    assert verify_report_bundle(bundle_root / request.run_id / "manifest.json").ok
    learning = LearningStore(tmp_path / "learning.jsonl", current_as_of=request.as_of)
    entries = reconcile_learning(request.run_id, result.state.analyst_reports, result.decision, request.as_of)
    for entry in entries:
        learning.record_evidence(entry)
    assert learning.inspect_asof_lessons(request.as_of, ("AAA",))

    identity = CheckpointIdentity(
        instrument=request.instrument,
        as_of=request.as_of,
        dataset_snapshot={"id": "mock-prices", "as_of": "2026-10-01", "digest": first_batch.data_fingerprint},
        analyst_set=request.analyst_roles,
        role_model_map={role: "offline/fixture-v1" for role in request.analyst_roles},
        skill_versions={"workflow": request.workflow_version},
        workflow_version=request.workflow_version,
        depth=1,
        rounds=1,
        config_digest=request.config_digest,
        research_plan_digest=stable_digest(request.research_plan),
    )
    checkpoint_state = ResearchRunState(
        run_id=request.run_id,
        current_state=ResearchState.EVIDENCE_REVIEW,
        as_of=request.as_of,
        state_history=(ResearchState.RECEIVED, ResearchState.IDENTIFIED, ResearchState.DATA_CHECKED, ResearchState.EVIDENCE_REVIEW),
        analyst_reports=result.state.analyst_reports,
    )
    store = ResearchRunStore(tmp_path / "checkpoints", workflow_version=request.workflow_version)
    store.save_checkpoint(checkpoint_state, identity)
    assert store.load_checkpoint(request.run_id, identity=identity) == checkpoint_state

    second_result = ResearchOrchestrator().run(
        request,
        _FiveRoleDriver(first_batch.data_fingerprint),
        _tools(second_batch),
        analyst_specs=tuple(AnalystSpec(role, required=True) for role in request.analyst_roles),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )
    second_manifest = ReportBundleWriter().write(second_result, tmp_path / "reports-second")
    assert {key: value for key, value in manifest.files.items() if key != "activity.jsonl"} == {
        key: value for key, value in second_manifest.files.items() if key != "activity.jsonl"
    }

    artifact_text = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "reports" / request.run_id).rglob("*") if path.is_file())
    for forbidden in ("example.test", "endpoint", "api_key", "SECRET", "prompt", "/Users/", "/tmp/"):
        assert forbidden not in artifact_text


def test_core_failure_blocks_decision_and_keeps_report_paper_only(tmp_path: Path) -> None:
    request = _request("capability-risk-failure")
    batch = _fetch_batch()
    result = ResearchOrchestrator().run(
        request,
        _FiveRoleDriver(batch.data_fingerprint),
        _tools(batch, risk_passes=False),
        analyst_specs=tuple(AnalystSpec(role, required=True) for role in request.analyst_roles),
        analyst_pool=AnalystPool(),
        manager=ResearchManager(),
    )
    assert result.state.current_state is ResearchState.VALIDATION_FAILED
    assert result.state.decision_eligible is False
    assert result.decision is None
    manifest = ReportBundleWriter().write(result, tmp_path / "reports")
    assert verify_report_bundle(tmp_path / "reports" / request.run_id / "manifest.json").ok
    assert "decision_digest" not in manifest.source_snapshot or manifest.source_snapshot["decision_digest"] is None
