"""Offline acceptance test for the governed research capability chain.

This test intentionally uses a user supplied mock JSON API and deterministic
fixtures.  It is the release gate for composition of Tasks 1 through 8; it
does not contact a provider, install an engine, or execute a live order.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

from finahinking.data.connection_settings import InMemoryDataCredentialStore
from finahinking.data.user_api import JsonApiConnector, TransportResponse
from finahinking.data.user_api_contracts import DataConnectionConfig, DataRequest
from finahinking.factors.dsl import parse_factor_expression
from finahinking.factors.mining import FactorCandidate
from finahinking.p6_6.workbench import ResearchCharter
from finahinking.quant.services import QuantServiceGateway
from finahinking.research.analyst_runtime import AnalystPool, ResearchManager
from finahinking.research.contracts import (
    AgentReport,
    CheckpointIdentity,
    FailureKind,
    ResearchPlan,
    ResearchRequest,
    ResearchRunState,
    ResearchState,
    stable_digest,
)
from finahinking.research.drivers import DriverResult, ModelDriver
from finahinking.research.factor_loop import FactorResearchState, run_factor_research
from finahinking.research.factor_proposals import (
    FactorHypothesis,
    FactorProposalCatalog,
    validate_factor_proposal,
)
from finahinking.research.learning import LearningStore, reconcile_learning
from finahinking.research.reports import ReportBundleWriter, verify_report_bundle
from finahinking.research.run_store import ResearchRunStore
from finahinking.research.tools import (
    ResearchToolGateway,
    ResearchToolRequest,
    ResearchToolResponse,
    ResearchToolStatus,
)
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
            assert dataset["records"][0] == {
                "instrument": "AAA", "timestamp": "2026-09-01T00:00:00Z",
                "available_at": "2026-09-01T00:00:00Z", "close": 107, "volume": 101,
            }
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
        quant.register("quant.run_backtest", self._backtest)
        quant.register("quant.analyze_risk", lambda params: {"passed": risk_passes, "max_drawdown": 0.08, "params": params})
        super().__init__(quant_gateway=quant)
        self.batch = batch
        self.normalized_input_digest = stable_digest(tuple(dict(record) for record in batch.records))
        self.quant_inputs = []

    def _backtest(self, params):
        assert self.normalized_input_digest in params["factor_ids"]
        self.quant_inputs.append(params)
        return {"engine": "finathink-deterministic", "oos": True, "passed": True, "params": params}

    def execute(self, request: ResearchToolRequest):
        response = super().execute(request)
        if request.name == "research.inspect_dataset" and response.result is not None:
            return replace(response, result={
                "dataset_id": request.args.get("dataset_id", "fixture"),
                "status": "AVAILABLE",
                "data_fingerprint": self.batch.data_fingerprint,
                "record_count": len(self.batch.records),
                "records": [dict(record) for record in self.batch.records],
            })
        return response


class _FailureTools(_FixtureTools):
    def __init__(self, batch, stage: str, failure_kind: FailureKind) -> None:
        super().__init__(batch)
        self.stage = stage
        self.failure_kind = failure_kind

    def execute(self, request: ResearchToolRequest):
        if request.name == self.stage:
            return ResearchToolResponse(
                request_id=request.run_id,
                name=request.name,
                status=ResearchToolStatus.FAILED,
                failure_kind=self.failure_kind,
                provenance={"fixture": "failure"},
            )
        return super().execute(request)


class _ProviderFailureDriver(ModelDriver):
    def propose(self, request: ResearchRequest, context: dict[str, object]) -> DriverResult:
        del request, context
        return DriverResult(failure_kind=FailureKind.PROVIDER_NOT_CONFIGURED, failure_message="fixture provider unavailable")


class _MissingRequiredDriver(ModelDriver):
    def propose(self, request: ResearchRequest, context: dict[str, object]) -> DriverResult:
        del context
        return DriverResult(reports=tuple(
            AgentReport(role=role, status="READY", evidence_refs=(f"artifact:fixture:{role}",))
            for role in request.analyst_roles if role != "technical"
        ))


def _tools(batch, *, risk_passes: bool = True) -> ResearchToolGateway:
    return _FixtureTools(batch, risk_passes=risk_passes)


def _fetch_batch():
    config = DataConnectionConfig(
        "mock-feed", "Mock fixture feed", "https://example.test/api", None, "no_auth",
        {"instrument": "ticker", "timestamp": "time", "available_at": "available", "close": "price", "volume": "qty"},
        "data",
    )
    payload = {"data": [
        {"ticker": "AAA", "time": f"2026-09-{day:02d}", "available": f"2026-09-{day:02d}", "price": str(100 + ((day * 7) % 11)), "qty": str(100 + day)}
        for day in range(1, 30)
    ]}
    connector = JsonApiConnector(config, InMemoryDataCredentialStore(), _MockTransport(payload), resolver=lambda host, port=None: ("93.184.216.34",))
    return connector.fetch(DataRequest("prices", ("AAA",), "2026-09-29", "2026-10-01", "2026-10-01"))


def _factor_run(batch, proposal):
    index = pd.DatetimeIndex([record["timestamp"] for record in batch.records])
    close = pd.Series([record["close"] for record in batch.records], index=index, dtype=float)
    frame = pd.DataFrame({"close": close}, index=index)
    assert frame["close"].tolist() == [100 + ((day * 7) % 11) for day in range(1, 30)]
    dataset = {"frame": frame, "forward_return": close.pct_change().shift(-1)}
    charter = ResearchCharter(
        charter_id="capability-factor-charter",
        research_question="Does fixture price strength survive costs?",
        hypothesis_scope="bounded momentum",
        dataset_reference=batch.data_fingerprint,
        data_split={"train": 0.6, "validation": 0.2, "test": 0.2},
        evaluation_metrics=("ic", "icir", "turnover"),
        hard_constraints={"shift_periods": 1, "paper_only": True},
        allowed_primitives=("input", "return", "rolling", "rank"),
        max_experiments=1,
        iteration_budget=1,
    )
    candidate = FactorCandidate(proposal.proposal_id, proposal.expression, "fixture momentum", "fixture", {"direction": "positive"})
    run = run_factor_research(charter, (candidate,), dataset)
    assert run.state is FactorResearchState.CANDIDATE_POOL
    assert run.rounds[0].train_evaluation is not None
    assert run.rounds[0].train_evaluation.oos_status == "HIDDEN"
    assert run.rounds[0].evaluation.oos_status == "HIDDEN"
    assert run.test_evaluation is None
    try:
        run.evaluate_test(dataset)
    except ValueError as exc:
        assert "frozen" in str(exc)
    else:
        raise AssertionError("unfrozen candidate exposed test evidence")
    frozen = run.freeze(candidate.candidate_id)
    tested = frozen.evaluate_test(dataset)
    assert tested.state is FactorResearchState.TEST_EVALUATED
    assert tested.test_evaluation is not None
    assert tested.test_evaluation.oos_status == "PASS"
    try:
        tested.evaluate_test(dataset)
    except ValueError as exc:
        assert "once-only" in str(exc)
    else:
        raise AssertionError("test evaluation was not once-only")
    assert tested.fingerprint
    return tested


def _assert_artifact_boundary(*roots: Path) -> None:
    forbidden = ("api_key", "token", "secret", "password", "endpoint", "prompt", "raw_provider_response")
    absolute = re.compile(r"(?:/(?:Users|home|tmp|private|etc|var|opt|root|Volumes|Applications|Library)/|[A-Za-z]:[\\/])")

    def check(value):
        assert value is None or isinstance(value, (str, bool, int, float, list, dict))
        if isinstance(value, dict):
            for key, item in value.items():
                assert isinstance(key, str)
                assert not any(name in key.casefold() for name in forbidden)
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
        elif isinstance(value, str):
            assert not absolute.search(value)
            assert not any(name in value.casefold() for name in forbidden)
            assert "example.test" not in value

    for root in roots:
        for path in ([root] if root.is_file() else root.rglob("*")):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            lowered = text.casefold()
            assert not any(item in lowered for item in forbidden), path
            assert not absolute.search(text), path
            assert "<object" not in lowered and " object at 0x" not in lowered and "raw provider response" not in lowered, path
            assert "example.test" not in lowered, path
            if path.suffix == ".json":
                check(json.loads(text))
            elif path.suffix == ".jsonl":
                for line in text.splitlines():
                    check(json.loads(line))
            elif path.suffix == ".html":
                HTMLParser(convert_charrefs=True).feed(text)


def test_offline_capability_vertical_slice_is_reproducible_and_recoverable(tmp_path: Path) -> None:
    first_batch, second_batch = _fetch_batch(), _fetch_batch()
    assert first_batch.data_fingerprint == second_batch.data_fingerprint
    assert first_batch.pit_available == "AVAILABLE"

    hypothesis = FactorHypothesis("momentum-fixture", "price momentum", "momentum", ("close",), 2, "positive")
    proposals = FactorProposalCatalog().propose(hypothesis, limit=2)
    assert proposals
    validate_factor_proposal(proposals[0])
    assert parse_factor_expression(proposals[0].expression, proposals[0].required_fields).fields
    factor_run = _factor_run(first_batch, proposals[0])
    assert factor_run.fingerprint == _factor_run(second_batch, proposals[0]).fingerprint
    normalized_input_digest = stable_digest(tuple(dict(record) for record in first_batch.records))
    assert normalized_input_digest == stable_digest(tuple(dict(record) for record in second_batch.records))

    request = _request()
    request = replace(request, research_plan=replace(request.research_plan, factor_ids=(factor_run.fingerprint, normalized_input_digest)))
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
    assert tools.quant_inputs[0]["factor_ids"] == [factor_run.fingerprint, normalized_input_digest]

    bundle_root = tmp_path / "reports"
    manifest = ReportBundleWriter().write(result, bundle_root)
    assert verify_report_bundle(bundle_root / request.run_id / "manifest.json").ok
    learning = LearningStore(tmp_path / "learning.jsonl", current_as_of=request.as_of)
    entries = reconcile_learning(request.run_id, result.state.analyst_reports, result.decision, request.as_of)
    for entry in entries:
        learning.record_evidence(entry)
    assert learning.inspect_asof_lessons(request.as_of, ("AAA",))
    assert learning.inspect_asof_lessons("2026-09-30", ("AAA",)) == ()
    assert LearningStore(tmp_path / "learning.jsonl").digest() == learning.digest()

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

    _assert_artifact_boundary(tmp_path / "reports" / request.run_id, tmp_path / "learning.jsonl", tmp_path / "checkpoints")


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


def test_release_failure_matrix_never_enters_paper_decision(tmp_path: Path) -> None:
    batch = _fetch_batch()
    request = _request("failure-matrix")
    cases = (
        ("data-unavailable", _FailureTools(batch, "research.inspect_dataset", FailureKind.DATA_UNAVAILABLE), _FiveRoleDriver(batch.data_fingerprint), "DATA_UNAVAILABLE"),
        ("no-data", _FailureTools(batch, "research.inspect_dataset", FailureKind.NO_DATA_AVAILABLE), _FiveRoleDriver(batch.data_fingerprint), "NO_DATA_AVAILABLE"),
        ("quant-failure", _FailureTools(batch, "quant.run_backtest", FailureKind.QUANT_VALIDATION_FAILED), _FiveRoleDriver(batch.data_fingerprint), "VALIDATION_FAILED"),
        ("risk-failure", _FailureTools(batch, "quant.analyze_risk", FailureKind.RISK_REVIEW_FAILED), _FiveRoleDriver(batch.data_fingerprint), "VALIDATION_FAILED"),
        ("provider-missing", _tools(batch), _ProviderFailureDriver(), "PROVIDER_NOT_CONFIGURED"),
        ("required-analyst-missing", _tools(batch), _MissingRequiredDriver(), "FAILED"),
    )
    for suffix, tools, driver, expected_state in cases:
        case_request = replace(request, run_id=f"failure-{suffix}")
        result = ResearchOrchestrator().run(
            case_request,
            driver,
            tools,
            analyst_specs=tuple(AnalystSpec(role, required=True) for role in case_request.analyst_roles),
            analyst_pool=AnalystPool(),
            manager=ResearchManager(),
        )
        assert result.state.current_state.value == expected_state
        assert result.decision is None
        assert result.state.decision_eligible is False
        assert ResearchState.PAPER_DECISION_READY not in result.state.state_history
        ReportBundleWriter().write(result, tmp_path / "matrix-reports")
        assert verify_report_bundle(tmp_path / "matrix-reports" / case_request.run_id / "manifest.json").ok
    _assert_artifact_boundary(tmp_path / "matrix-reports")
