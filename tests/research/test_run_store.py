from __future__ import annotations

import json
from datetime import UTC, date, datetime

import pytest

from finahinking.research.contracts import (
    AgentReport,
    CheckpointIdentity,
    ResearchPlan,
    ResearchRequest,
    ResearchRunState,
    ResearchState,
    RunEvent,
)
from finahinking.research.drivers import OfflineDriver
from finahinking.research.run_store import (
    CheckpointCorruptError,
    CheckpointIdentityMismatch,
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
