from __future__ import annotations

from datetime import date

from finahinking.research.contracts import (
    AgentReport,
    ReportManifest,
    ResearchRunState,
    ResearchState,
)
from finahinking.research.reports import compare_report_manifests, verify_report_bundle
from finahinking.research.ui import render_status_wall_html, research_view_model


def _state(state: ResearchState = ResearchState.ANALYSTS_RUNNING) -> ResearchRunState:
    return ResearchRunState(
        run_id="run-wall",
        current_state=state,
        as_of=date(2026, 10, 1),
        state_history=(ResearchState.RECEIVED, ResearchState.DATA_CHECKED, state),
        analyst_reports=(
            AgentReport("fundamentals", "READY", evidence_refs=("artifact:f",)),
            AgentReport("technical", "FAILED", limitations=("missing evidence",)),
        ),
        decision_eligible=state is ResearchState.LEARNING_RECORDED,
    )


def _manifest(**snapshot) -> ReportManifest:
    return ReportManifest(
        run_id="run-wall",
        schema_version="research-report.v1",
        files={"complete_report.html": "digest-a", "activity.jsonl": "digest-events"},
        source_snapshot={"as_of": "2026-10-01", **snapshot},
        created_at="2026-10-01T00:00:00+00:00",
    )


def test_view_model_exposes_redacted_role_stage_checkpoint_and_provider_facts() -> None:
    model = research_view_model(
        _state(),
        _manifest(
            role_status={"fundamentals": "READY", "technical": "FAILED"},
            stage_status={"analysts": "PARTIAL", "evidence": "BLOCKED"},
            missing_evidence=["technical:artifact:price"],
            checkpoint_status={"state": "SAVED", "path": "/Users/mac/private/checkpoint.json"},
            factor_proposals=[{"proposal_id": "p-1", "status": "VALIDATED", "digest": "factor-digest"}],
            provider_readiness={"provider": "user", "status": "CONFIGURED", "credential_ref": "USER_KEY"},
            prompt="never expose this",
        ),
    )
    assert model["role_status"]["fundamentals"] == "READY"
    assert model["stage_status"]["evidence"] == "BLOCKED"
    assert model["missing_evidence"] == ["technical:artifact:price"]
    assert model["checkpoint_status"]["state"] == "SAVED"
    assert "private" not in str(model)
    assert "never expose" not in str(model)
    assert model["factor_proposals"][0]["proposal_id"] == "p-1"
    assert model["provider_readiness"]["credential_ref"] == "USER_KEY"


def test_status_wall_html_is_readable_without_javascript_and_never_claims_strategy_superiority() -> None:
    model = research_view_model(_state(ResearchState.CANCELLED), _manifest(stage_status={"cancel": "CANCELLED"}))
    html = render_status_wall_html(model)
    assert "fundamentals" in html
    assert "CANCELLED" in html
    assert "<noscript>" in html
    assert "better" not in html.lower()
    assert "superior" not in html.lower()
    assert "api_key" not in html.lower()


def test_compare_report_manifests_only_returns_digests_metrics_and_limitations() -> None:
    left = {
        "run_id": "left",
        "schema_version": "research-report.v1",
        "files": {"complete_report.html": "aaa"},
        "source_snapshot": {"state_digest": "state-a", "metrics": {"ic": 0.1}, "limitations": ["fixture"]},
    }
    right = {
        "run_id": "right",
        "schema_version": "research-report.v1",
        "files": {"complete_report.html": "bbb"},
        "source_snapshot": {"state_digest": "state-b", "metrics": {"ic": 0.2}, "limitations": ["fixture", "short sample"]},
    }
    comparison = compare_report_manifests(left, right)
    assert comparison["left"]["metrics"] == {"ic": 0.1}
    assert comparison["right"]["limitations"] == ["fixture", "short sample"]
    assert comparison["differences"]["files"]["complete_report.html"] == {"left": "aaa", "right": "bbb"}
    assert "better" not in str(comparison).lower()
    assert "superior" not in str(comparison).lower()
    assert "prompt" not in str(comparison).lower()


def test_compare_report_manifests_rejects_secret_bearing_payload() -> None:
    try:
        compare_report_manifests({"run_id": "x", "api_key": "secret"}, _manifest())
    except ValueError as exc:
        assert "secret" in str(exc).lower() or "sensitive" in str(exc).lower()
    else:
        raise AssertionError("secret-bearing manifest was accepted")


def test_verifier_requires_fixed_report_tree(tmp_path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"schema_version":"research-report.v1","files":{"complete_report.html":"x","activity.jsonl":"y"}}',
        encoding="utf-8",
    )
    verification = verify_report_bundle(manifest)
    assert verification.ok is False
    assert any("1_analysts/fundamentals.html" in error for error in verification.errors)
