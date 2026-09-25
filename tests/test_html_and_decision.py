import csv
import json
import subprocess
import sys

import pytest


def test_html_is_offline_and_decision_table_is_complete(ROOT, CONFIG, MANIFEST, tmp_path):
    output = tmp_path / "artifacts"
    script = ROOT / "scripts" / "generate_financial_html.py"
    analysis = ROOT / "examples" / "demo_analysis.json"
    subprocess.run([sys.executable, str(script), str(analysis), "--config", str(CONFIG), "--manifest", str(MANIFEST), "--output-dir", str(output), "--decision-format", "both"], check=True)
    html = (output / "financial_research_brief.html").read_text(encoding="utf-8")
    assert "spy-tlt-gld-20260926-exp001" in html
    assert "complete" in html
    assert "DM" in html and "PBO" in html
    assert "风险与尾部指标" in html
    assert "<script" not in html and "<link" not in html
    with (output / "decision_table.csv").open(encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle))
    assert header == ["priority", "module", "current_view", "action", "trigger", "evidence", "risk", "horizon", "next_check", "experiment_id", "reproducibility_status"]


def test_analysis_without_overfit_fields_fails(ROOT, tmp_path):
    data = {"meta": {}, "summary": {}, "forecast": {}, "charts": [], "modules": [], "decision_rows": []}
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_financial_html.py"), str(path)], capture_output=True, text=True)
    assert result.returncode != 0
