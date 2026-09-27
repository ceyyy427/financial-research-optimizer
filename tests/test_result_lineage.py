import json
import hashlib

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


def test_recompute_mode_executes_declared_command_and_checks_output_hash(tmp_path):
    output = tmp_path / "metric.out"
    output.write_text("stable\n", encoding="utf-8")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    data = {
        "result_lineage": {"status": "pass", "metrics": [{
            "metric_id": "m1", "value": 1, "calculation_id": "c1",
            "input_hash": "sha256:input", "code_version": "code@1",
            "formula": "1", "source_ids": ["synthetic"],
            "recompute_command": "python3 -c pass", "output_file": str(output),
            "output_hash": "sha256:" + digest,
        }]}
    }
    assert verify_result_lineage(data, recompute=True, cwd=tmp_path)["status"] == "pass"
