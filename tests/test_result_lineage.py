import json

from verify_result_lineage import verify_result_lineage


def test_demo_result_lineage_passes(ROOT):
    data = json.loads((ROOT / "examples" / "demo_analysis.json").read_text(encoding="utf-8"))
    assert verify_result_lineage(data)["status"] == "pass"


def test_numeric_chart_without_lineage_is_rejected(ROOT):
    data = json.loads((ROOT / "examples" / "demo_analysis.json").read_text(encoding="utf-8"))
    data["charts"][0].pop("lineage_refs")
    audit = verify_result_lineage(data)
    assert audit["status"] == "failed"
    assert any("charts[0]" in error for error in audit["errors"])
