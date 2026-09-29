import asyncio
import csv
import json
from pathlib import Path

from adapters.sdmx import SdmxAdapter
from maturity_report import build_report
from parsers.stats_gov_json import parse_stats_gov_json
from financial_research.runtime import run_research


ROOT = Path(__file__).resolve().parents[1]


def test_stats_v2_parser_expands_period_values():
    rows = parse_stats_gov_json({"data": [{"code": "202608MM", "values": [{"value": "101.2", "du_name": "%"}]}]}, instrument_id="CPI", source_url="https://data.stats.gov.cn/")
    assert rows[0]["observation_time"] == "2026-08-01"
    assert rows[0]["point_in_time_status"] == "not_available"


def test_v090_maturity_report_exposes_three_explicit_fallbacks():
    report = build_report(ROOT / "config/source_registry.yaml")
    assert report["counts"]["degraded_execution_count"] == 3
    assert "degraded" in report["routing_states"]


def test_research_grade_forecast_compares_three_baselines(tmp_path):
    dataset = tmp_path / "prices.csv"
    with dataset.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "value", "availability_time"])
        writer.writeheader()
        for index, value in enumerate([10, 11, 10, 12, 13, 12, 14, 15]):
            writer.writerow({"date": f"2026-01-{index + 1:02d}", "value": value, "availability_time": f"2026-01-{index + 1:02d}T16:00:00Z"})
    result = asyncio.run(run_research(task="forecast", mode="forecasting", output_level="research_grade", target="value", horizon="1d", dataset_path=str(dataset), artifact_dir=str(tmp_path / "artifacts"), require_point_in_time=True, run_root=str(tmp_path / "runs")))
    assert result["execution"]["status"] == "completed"
    rolling = json.loads((tmp_path / "artifacts" / "rolling_evaluation.json").read_text(encoding="utf-8"))
    assert {item["model_id"] for item in rolling["models"]} == {"historical_mean_baseline", "naive_last_value", "rolling_mean_baseline"}
    assert rolling["calibration_status"] == "not_calibrated"
    assert "interval_method" in rolling
