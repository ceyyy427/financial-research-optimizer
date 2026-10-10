from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime

from finahinking.local_app import LocalAppConfig, LocalApplication
from finahinking.research.contracts import (
    AgentReport,
    ReportManifest,
    ResearchRunResult,
    ResearchRunState,
    ResearchState,
    RunEvent,
)
from finahinking.research.reports import ReportBundleWriter, compare_experiments
from finahinking.research.ui import research_runtime_view_model


def _result() -> ResearchRunResult:
    state = ResearchRunState(
        run_id="stream-run",
        current_state=ResearchState.ANALYSTS_RUNNING,
        as_of=date(2026, 10, 1),
        state_history=(ResearchState.RECEIVED, ResearchState.DATA_CHECKED, ResearchState.ANALYSTS_RUNNING),
        analyst_reports=(AgentReport("technical", "READY", evidence_refs=("artifact:technical",)),),
    )
    events = (
        RunEvent(
            "event-1",
            "stream-run",
            ResearchState.ANALYSTS_RUNNING,
            "worker",
            datetime(2026, 10, 1, tzinfo=UTC),
            "digest-1",
            metadata={
                "tool_summary": {"name": "factor_scan", "status": "COMPLETE"},
                "retry_count": 2,
                "checkpoint_status": {"state": "SAVED", "checkpoint_digest": "cp-1"},
                "learning_proposal": {"status": "NO_LEARNING_UPDATE"},
            },
        ),
    )
    return ResearchRunResult(state=state, events=events)


def test_runtime_view_model_exposes_server_owned_stage_tool_retry_checkpoint_and_manifest_digest() -> None:
    result = _result()
    manifest = ReportManifest(
        run_id=result.state.run_id,
        schema_version="research-report.v1",
        files={"complete_report.html": "digest"},
        source_snapshot={"metrics": {"ic": 0.1}},
        created_at="2026-10-01T00:00:00+00:00",
    )
    model = research_runtime_view_model(result.state.run_id, state=result.state, manifest=manifest, events=result.events)
    assert model["run_id"] == "stream-run"
    assert model["paper_only"] is True
    assert model["stage_status"]["analysts"] == "CURRENT"
    assert model["tool_summaries"][0]["name"] == "factor_scan"
    assert model["retries"]["count"] == 2
    assert model["checkpoint"]["state"] == "SAVED"
    assert model["learning_proposal"]["status"] == "NO_LEARNING_UPDATE"
    assert len(model["manifest_digest"]) == 64
    assert "prompt" not in str(model).lower()


def test_compare_experiments_only_returns_inputs_metrics_and_limitations() -> None:
    comparison = compare_experiments(
        [
            {"run_id": "a", "inputs": {"dataset_digest": "d1"}, "metrics": {"ic": 0.1}, "limitations": ["short sample"]},
            {"run_id": "b", "inputs": {"dataset_digest": "d2"}, "metrics": {"ic": 0.2}, "limitations": ["short sample", "fixture"]},
        ]
    )
    assert comparison["runs"][0]["inputs"] == {"dataset_digest": "d1"}
    assert comparison["runs"][1]["metrics"] == {"ic": 0.2}
    assert comparison["runs"][1]["limitations"] == ["fixture", "short sample"]
    assert "recommendation" not in comparison
    assert "better" not in str(comparison).lower()
    assert "strategy" not in str(comparison).lower()


def test_local_app_exposes_read_only_runtime_stream(tmp_path) -> None:
    app = LocalApplication(LocalAppConfig(db_path=":memory:", offline=True), connection=sqlite3.connect(":memory:"))
    result = _result()
    manifest = ReportBundleWriter().write(result, app.artifact_root / "reports")
    app.register_research_run(result, manifest)
    status, content_type, payload = app.route("GET", "/api/research/runs/stream-run/stream")
    assert (status, content_type) == (200, "application/json")
    assert payload["run_id"] == "stream-run"
    assert payload["paper_only"] is True
    rejected, _, error = app.route("POST", "/api/research/runs/stream-run/stream", body={})
    assert rejected == 405
    assert "read-only" in error["error"]
