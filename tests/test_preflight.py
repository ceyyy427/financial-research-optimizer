import json

import pytest

from run_preflight import run_preflight


def test_research_grade_preflight_is_ready(CONFIG, MANIFEST, ROOT):
    result = run_preflight(CONFIG, MANIFEST, ROOT / "examples" / "demo_analysis.json")
    assert result["status"] == "ready"
    assert result["output_level"] == "research_grade"


def test_portfolio_grade_preflight_blocks_without_dataset(CONFIG, MANIFEST, ROOT, tmp_path):
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    data["output_level"] = "portfolio_grade"
    data["preflight"] = {"require_manifest": True, "require_dataset": True, "require_reconciliation": True}
    config = tmp_path / "portfolio_config.json"
    config.write_text(json.dumps(data), encoding="utf-8")
    result = run_preflight(config, MANIFEST, ROOT / "examples" / "demo_analysis.json")
    assert result["status"] == "blocked"
    assert any("dataset" in reason for reason in result["blocking_reasons"])


def test_dynamic_preflight_exposes_degraded_status(CONFIG, MANIFEST, ROOT, tmp_path):
    freshness = tmp_path / "freshness.json"
    freshness.write_text(json.dumps({"status": "degraded", "reason": "provider switched"}), encoding="utf-8")
    result = run_preflight(CONFIG, MANIFEST, ROOT / "examples" / "demo_analysis.json", freshness_path=freshness)
    assert result["status"] == "degraded"
    assert any(check["check_id"] == "freshness" for check in result["checks"])
