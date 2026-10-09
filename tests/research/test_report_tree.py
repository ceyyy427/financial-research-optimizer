from __future__ import annotations

import json
from datetime import UTC, date, datetime

from finahinking.research.contracts import AgentReport, ResearchRunResult, ResearchRunState, ResearchState, RunEvent
from finahinking.research.reports import ReportBundleWriter, verify_report_bundle
from finahinking.research.ui import research_runtime_view_model


def _result(state: ResearchState = ResearchState.RISK_REVIEW) -> ResearchRunResult:
    run_state = ResearchRunState(
        run_id="tree-run",
        current_state=state,
        as_of=date(2026, 10, 9),
        state_history=(ResearchState.RECEIVED, ResearchState.DATA_CHECKED, state),
        analyst_reports=(AgentReport("technical", "READY", evidence_refs=("artifact:price",)),),
        decision_eligible=False,
    )
    event = RunEvent(
        "event-tree", "tree-run", state, "workflow", datetime(2026, 10, 9, tzinfo=UTC), "digest",
        metadata={
            "experiments": [{"experiment_id": "exp-1", "status": "COMPLETE", "metrics": {"ic": 0.1}}],
            "risk_attribution": {"status": "RECORDED", "factors": [{"name": "volatility", "contribution": 0.2}]},
            "learning_history": [{"card_id": "learn-1", "status": "RECORDED"}],
        },
    )
    return ResearchRunResult(state=run_state, events=(event,))


def test_write_runtime_tree_publishes_navigable_runtime_pages_and_consistent_digests(tmp_path):
    writer = ReportBundleWriter(output_root=tmp_path / "reports")
    manifest = writer.write_runtime_tree(_result())
    bundle = tmp_path / "reports" / "tree-run"
    for relative in ("experiments/index.html", "risk_attribution/index.html", "learning_history/index.html"):
        assert relative in manifest.files
        assert (bundle / relative).exists()
        assert __import__("hashlib").sha256((bundle / relative).read_bytes()).hexdigest() == manifest.files[relative]
    assert verify_report_bundle(bundle / "manifest.json").ok


def test_runtime_tree_marks_missing_stages_explicitly(tmp_path):
    result = _result(ResearchState.ANALYSTS_RUNNING)
    manifest = ReportBundleWriter(output_root=tmp_path / "reports").write_runtime_tree(result)
    bundle = tmp_path / "reports" / "tree-run"
    for relative in ("experiments/index.html", "risk_attribution/index.html", "learning_history/index.html"):
        html = (bundle / relative).read_text(encoding="utf-8")
        assert "PENDING" in html or "BLOCKED" in html
    model = research_runtime_view_model("tree-run", state=result.state, manifest=manifest, events=result.events)
    assert "experiments" in model and "risk_attribution" in model and "learning_history" in model


def test_runtime_payload_is_redacted_and_schema_versioned():
    result = _result()
    model = research_runtime_view_model(
        result.state,
        manifest={"run_id": "tree-run", "schema_version": "research-report.v1", "files": {}, "source_snapshot": {}},
        events=result.events,
    )
    assert model["schema_version"] == 3
    assert model["experiments"][0]["experiment_id"] == "exp-1"
    assert "api_key" not in json.dumps(model).lower()
