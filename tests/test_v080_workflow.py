import asyncio
import csv
import json
from datetime import datetime, timezone

from financial_research.runtime import run_research
from scripts.agent.handlers import _data_capture
from scripts.adapters.factory import ContractOnlyAdapter, build_request
from scripts.adapters.evidence import evaluate_maturity, get_evidence
from scripts.browser.security import validate_public_https_url, validate_redirect


def _dataset(path, with_availability=False):
    fields = ["date", "close"] + (["availability_time"] if with_availability else [])
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for index, value in enumerate((100, 101, 99, 102, 103)):
            row = [f"2026-01-0{index + 1}", value]
            if with_availability:
                row.append(f"2026-01-0{index + 1}T16:00:00Z")
            writer.writerow(row)


def test_default_forecasting_runs_without_custom_handlers(tmp_path):
    source = tmp_path / "prices.csv"
    _dataset(source)
    result = asyncio.run(run_research("forecast local prices", mode="forecasting", output_level="standard", dataset_path=str(source), artifact_dir=str(tmp_path / "out"), run_root=None))
    assert result["execution"]["status"] == "completed"
    names = {path.name for path in (tmp_path / "out").iterdir()}
    assert {"analysis.json", "rolling_evaluation.json", "financial_research_brief.html", "decision_table.csv", "decision_table.md"} <= names
    analysis = json.loads((tmp_path / "out" / "analysis.json").read_text())
    assert analysis["result_lineage"]["metrics"][0]["input_hash"]


def test_missing_availability_time_blocks_when_required(tmp_path):
    source = tmp_path / "macro.csv"
    _dataset(source)
    result = asyncio.run(run_research("point in time forecast", mode="forecasting", output_level="standard", dataset_path=str(source), artifact_dir=str(tmp_path / "out"), run_root=None, execution_mode="execution", require_point_in_time=True))
    audit = next(item for item in result["execution"]["results"] if item["node_id"] == "point_in_time_audit")
    assert audit["status"] == "blocked"
    assert audit["reason_code"] == "MISSING_AVAILABILITY_TIME"
    assert audit["next_action"]


def test_availability_time_is_preserved_in_canonical_and_features(tmp_path):
    source = tmp_path / "prices.csv"
    _dataset(source, with_availability=True)
    result = asyncio.run(run_research("point in time forecast", mode="forecasting", output_level="standard", dataset_path=str(source), artifact_dir=str(tmp_path / "out"), run_root=None, execution_mode="execution", require_point_in_time=True))
    assert result["execution"]["status"] == "completed"
    canonical = json.loads((tmp_path / "out" / "canonical_dataset.json").read_text())
    features = json.loads((tmp_path / "out" / "features.json").read_text())
    assert canonical[0]["point_in_time_status"] == "pass"
    assert features["lineage"]["point_in_time_status"] == "verified"


def test_capture_without_source_is_structured_blocked():
    result = _data_capture({}, {"id": "data_capture"})
    assert result["status"] == "blocked"
    assert result["reason_code"] == "CAPABILITY_GAP"
    assert result["next_action"]
    assert result["user_action_required"] is True


def test_explicit_verified_snapshot_fallback_is_executable(tmp_path):
    snapshot = tmp_path / "sse.csv"
    snapshot.write_text("date,close,volume\n2026-01-01,10,100\n", encoding="utf-8")
    profile = {"source_id": "sse", "primary_method": "official_file", "access_policy": "public", "implementation_status": "partial", "parser_status": "available"}
    request = build_request("sse", {"fallback_file": str(snapshot)})
    result = ContractOnlyAdapter(profile).fetch(request)
    assert result.quality_status == "usable_with_warning"
    assert result.provenance["fallback_used"] is True
    assert result.raw_snapshot["snapshot_hash"].startswith("sha256:")


def test_l4_requires_revision_and_expiry_downgrades_only_to_l3():
    profile = {"source_id": "sec_edgar", "primary_method": "api", "implementation_status": "production", "parser_status": "tested", "point_in_time": True}
    evidence = {"contract_status": "complete", "fixture_status": "passed", "integration_status": "passed", "quality_gate_status": "passed", "live_smoke_status": "passed", "health_status": "healthy", "freshness_status": "fresh", "point_in_time_status": "verified", "revision_status": "not_run", "snapshot_hash": "hash", "last_live_success_at": "now", "certification_expires_at": "2099-01-01T00:00:00Z"}
    result = evaluate_maturity(profile, "sec_edgar", "company_facts", evidence, True, True)
    assert result["automatic_execution_ready"] is True
    assert result["live_certified"] is False
    evidence["revision_status"] = "verified"
    evidence["certification_expires_at"] = "2020-01-01T00:00:00Z"
    result = evaluate_maturity(profile, "sec_edgar", "company_facts", evidence, True, True)
    assert result["automatic_execution_ready"] is True
    assert result["live_certified"] is False


def test_evidence_identity_does_not_cross_dataset_or_access_method():
    records = {
        ("sec_edgar", "company_facts", "api"): {"source_id": "sec_edgar", "dataset_id": "company_facts", "access_method": "api"},
        ("sec_edgar", "submissions", "api"): {"source_id": "sec_edgar", "dataset_id": "submissions", "access_method": "api"},
    }
    assert get_evidence("sec_edgar", "company_facts", "api", records)["dataset_id"] == "company_facts"
    assert get_evidence("sec_edgar", "company_facts", "browser", records) == {}


def test_browser_security_rejects_local_and_cross_origin_redirect():
    try:
        validate_public_https_url("https://127.0.0.1/data")
        assert False, "private address should be blocked"
    except ValueError:
        pass
    validate_public_https_url("https://example.com/data")
    try:
        validate_redirect("https://example.com/data", "https://other.example/data")
        assert False, "cross-origin redirect should be blocked"
    except ValueError:
        pass
