from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest

from finahinking.quant.services import QuantServiceGateway
from finahinking.research.contracts import (
    AgentReport,
    CheckpointIdentity,
    ResearchPlan,
    ResearchRequest,
    ResearchRunState,
    ResearchState,
    RunEvent,
    validate_transition,
)
from finahinking.research.drivers import OfflineDriver
from finahinking.research.run_store import (
    CheckpointCorruptError,
    CheckpointIdentityMismatch,
    CheckpointIncompatibleError,
    CompletedRunError,
    ResearchRunStore,
    RunControl,
)
from finahinking.research.tools import ResearchToolGateway
from finahinking.research.workflow import ResearchOrchestrator


def identity(*, roles: tuple[str, ...] = ("technical", "fundamentals")) -> CheckpointIdentity:
    return CheckpointIdentity(
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        dataset_snapshot={"id": "prices-001", "as_of": "2026-09-30", "digest": "dataset-v1"},
        analyst_set=roles,
        role_model_map={role: "offline/fixture-v1" for role in roles},
        skill_versions={"workflow": "research.v1"},
        workflow_version="research.v1",
        depth=2,
        rounds=3,
        config_digest="cfg-001",
        research_plan_digest="plan-001",
    )


def state(run_id: str = "run-001", current: ResearchState = ResearchState.EVIDENCE_REVIEW) -> ResearchRunState:
    return ResearchRunState(
        run_id=run_id,
        current_state=current,
        as_of=date(2026, 10, 1),
        state_history=(ResearchState.RECEIVED, ResearchState.IDENTIFIED, current),
        analyst_reports=(
            AgentReport(
                role="technical",
                status="READY",
                claims=("historical observation",),
                evidence_refs=("artifact:technical",),
                model_ref="offline/fixture-v1",
            ),
        ),
    )


def event(run_id: str = "run-001", event_id: str = "event-1") -> RunEvent:
    return RunEvent(
        event_id=event_id,
        run_id=run_id,
        state=ResearchState.EVIDENCE_REVIEW,
        actor="workflow",
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
        payload_digest="payload-001",
        metadata={"stage_owner": "research_manager"},
    )


def test_checkpoint_round_trip_and_identity_validation(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    original = state()
    expected = identity()

    path = store.save_checkpoint(original, expected)

    assert path.name == "run-001.json"
    assert store.load_checkpoint("run-001") == original
    assert store.load_checkpoint("run-001", identity=expected) == original
    with pytest.raises(CheckpointIdentityMismatch):
        store.load_checkpoint("run-001", identity=identity(roles=("news",)))


def test_cancellation_is_legal_from_every_resumable_intermediate_state() -> None:
    for current in (
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
    ):
        validate_transition(current, ResearchState.CANCELLED)


def test_load_record_rejects_store_workflow_and_provider_capability_mismatch(tmp_path) -> None:
    writer = ResearchRunStore(tmp_path, workflow_version="research.v1", provider_capability_digest="cap-v1")
    writer.save_checkpoint(state(), identity())

    with pytest.raises(CheckpointIncompatibleError):
        ResearchRunStore(tmp_path, workflow_version="research.v2", provider_capability_digest="cap-v1").load_record("run-001")
    with pytest.raises(CheckpointIdentityMismatch):
        ResearchRunStore(tmp_path, workflow_version="research.v1", provider_capability_digest="cap-v2").load_record("run-001")


def test_default_store_rejects_forged_provider_capability_digest(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    path = store.save_checkpoint(state(), identity())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["provider_capability_digest"] = "forged-capability"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CheckpointIdentityMismatch):
        store.load_record("run-001")


def test_completed_checkpoint_cannot_be_resumed(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    expected = identity()

    path = store.save_checkpoint(state(), expected)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["state"]["current_state"] = ResearchState.REPORT_PUBLISHED.value
    payload["state"]["state_history"][-1] = ResearchState.REPORT_PUBLISHED.value
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CompletedRunError):
        store.load_checkpoint("run-001")


def test_cancel_is_typed_and_does_not_delete_artifact(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    store.save_checkpoint(state(), identity())
    control = RunControl()

    assert control.cancel("run-001") is True
    assert control.is_cancelled("run-001") is True
    assert (tmp_path / "run-001.json").exists()
    assert control.cancel("run-001") is False


def test_workflow_turns_a_cancel_token_into_cancelled_state() -> None:
    request = ResearchRequest(
        run_id="run-cancelled",
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(required_datasets=("fixture-prices",)),
        analyst_roles=("technical",),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg",
    )
    control = RunControl()
    control.cancel(request.run_id)

    result = ResearchOrchestrator().run(request, OfflineDriver(), ResearchToolGateway(), run_control=control)

    assert result.state.current_state is ResearchState.CANCELLED
    assert result.state.failure_kind.value == "CANCELLED"


def test_events_are_append_only_and_stably_serialized(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    store.append_event(event(event_id="event-2"))
    store.append_event(event(event_id="event-1"))

    path = tmp_path / "events.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["event_id"] for line in lines] == ["event-2", "event-1"]
    assert all("prompt" not in line and "secret" not in line for line in lines)


def test_corrupt_event_jsonl_returns_typed_failure(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    path = tmp_path / "events.jsonl"
    path.write_text('{"event_id":"ok"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(CheckpointCorruptError):
        store.read_events()


def test_checkpoint_rejects_secret_prompt_and_raw_provider_fields(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    secret_identity = CheckpointIdentity(
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        dataset_snapshot={"id": "prices", "prompt": "do not persist", "raw_provider_response": {"x": 1}},
        analyst_set=("technical",),
        role_model_map={"technical": "offline/fixture-v1"},
        skill_versions={},
        workflow_version="research.v1",
        depth=1,
        rounds=1,
        config_digest="cfg",
        research_plan_digest="plan",
    )

    with pytest.raises(ValueError, match="checkpoint payload"):
        store.save_checkpoint(state(), secret_identity)


def test_checkpoint_rejects_sensitive_strings_even_when_field_name_is_safe(tmp_path) -> None:
    unsafe = ResearchRunState(
        run_id="run-001",
        current_state=ResearchState.EVIDENCE_REVIEW,
        as_of=date(2026, 10, 1),
        state_history=(ResearchState.RECEIVED, ResearchState.IDENTIFIED, ResearchState.EVIDENCE_REVIEW),
        analyst_reports=(
            AgentReport(
                role="technical",
                status="READY",
                claims=("api_key=super-secret", "prompt: raw provider response"),
                evidence_refs=("artifact:technical",),
                model_ref="provider/model-v1",
            ),
        ),
        failure_message="raw provider response: token=abc",
    )

    with pytest.raises(ValueError, match="checkpoint payload"):
        ResearchRunStore(tmp_path).save_checkpoint(unsafe, identity())


@pytest.mark.parametrize("value", ("/etc/passwd", "src/foo.py", "src/foo", "provider response", "provider_response", "raw_response"))
def test_checkpoint_rejects_path_and_provider_response_strings(tmp_path, value: str) -> None:
    unsafe = ResearchRunState(
        run_id="run-001",
        current_state=ResearchState.EVIDENCE_REVIEW,
        as_of=date(2026, 10, 1),
        state_history=(ResearchState.RECEIVED, ResearchState.IDENTIFIED, ResearchState.EVIDENCE_REVIEW),
        analyst_reports=(
            AgentReport(
                role="technical",
                status="READY",
                claims=(value,),
                evidence_refs=("artifact:technical",),
                model_ref="provider/model-v1",
            ),
        ),
    )

    with pytest.raises(ValueError, match="checkpoint payload"):
        ResearchRunStore(tmp_path).save_checkpoint(unsafe, identity())


def test_checkpoint_rejects_unknown_fields_in_payload(tmp_path) -> None:
    store = ResearchRunStore(tmp_path)
    path = store.save_checkpoint(state(), identity())
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["unexpected"] = "malicious extension"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CheckpointCorruptError):
        store.load_checkpoint("run-001")


def _quant_tools() -> ResearchToolGateway:
    gateway = QuantServiceGateway()
    gateway.register("quant.run_backtest", lambda params: {"annual_return": 0.1, "oos": True})
    gateway.register("quant.analyze_risk", lambda params: {"passed": True, "max_drawdown": 0.08})
    return ResearchToolGateway(quant_gateway=gateway)


def _workflow_request(run_id: str) -> ResearchRequest:
    return ResearchRequest(
        run_id=run_id,
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(required_datasets=("fixture-prices",)),
        analyst_roles=("technical",),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg",
    )


@pytest.mark.parametrize("hook", ("risk", "decision"))
def test_workflow_cancellation_during_risk_or_decision_cannot_reach_learning(hook: str) -> None:
    control = RunControl()

    class CancellingOrchestrator(ResearchOrchestrator):
        def run_risk_review(self, plan, quant_result):
            result = super().run_risk_review(plan, quant_result)
            if hook == "risk":
                control.cancel("run-late-cancel")
            return result

        def make_paper_decision(self, risk_review, reports, quant_result, instrument):
            result = super().make_paper_decision(risk_review, reports, quant_result, instrument)
            if hook == "decision":
                control.cancel("run-late-cancel")
            return result

    result = CancellingOrchestrator().run(
        _workflow_request("run-late-cancel"), OfflineDriver(), _quant_tools(), run_control=control
    )

    assert result.state.current_state is ResearchState.CANCELLED
    assert result.decision is None
    assert ResearchState.LEARNING_RECORDED not in result.state.state_history


@pytest.mark.parametrize("cancel_state", (ResearchState.REPORT_PUBLISHED, ResearchState.LEARNING_RECORDED))
def test_workflow_cancellation_during_publication_or_learning_is_not_reported_complete(cancel_state: ResearchState) -> None:
    control = RunControl()

    class CancellingOrchestrator(ResearchOrchestrator):
        @staticmethod
        def _event(run_id, state, actor, payload, *, metadata=None):
            event = ResearchOrchestrator._event(run_id, state, actor, payload, metadata=metadata)
            if state is cancel_state:
                control.cancel(run_id)
            return event

    result = CancellingOrchestrator().run(
        _workflow_request("run-publication-cancel"), OfflineDriver(), _quant_tools(), run_control=control
    )

    assert result.state.current_state is ResearchState.CANCELLED
    assert result.decision is None
    assert ResearchState.LEARNING_RECORDED not in result.state.state_history
