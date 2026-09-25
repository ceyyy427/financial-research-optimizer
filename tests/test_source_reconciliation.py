import csv

from reconcile_sources import reconcile
from config_utils import load_config


FIELDS = ["instrument_id", "observation_date", "close", "volume", "adjustment_code", "effective_timestamp"]


def write_source(path, close):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow({"instrument_id": "SPY", "observation_date": "2026-01-05", "close": str(close), "volume": "1000", "adjustment_code": "adjusted", "effective_timestamp": "2026-01-05T21:00:00Z"})


def test_material_source_conflict_blocks_analysis(CONFIG, tmp_path):
    first, second = tmp_path / "a.csv", tmp_path / "b.csv"
    write_source(first, 100.0)
    write_source(second, 102.0)
    result = reconcile({"official_exchange": first, "public_aggregator": second}, load_config(CONFIG))
    assert result["summary"]["counts"]["material_conflict"] == 1
    assert result["summary"]["stop_dependency_analysis"] is True
