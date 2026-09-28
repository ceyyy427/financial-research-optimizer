from pathlib import Path

import pytest

from adapters.factory import AdapterNotReady, build_adapter, build_request, fetch_with_adapter
from adapters.protocol import SourceRequest, SourceResult
from adapters.status import adapter_status
from run_adapter_smoke import replay
from source_router import SourceRouter


ROOT = Path(__file__).resolve().parents[1]


def test_source_request_is_explicit_and_serializable():
    request = SourceRequest(
        source_id="fred",
        dataset="series_observations",
        instrument="GDP",
        as_of="2026-09-26",
        authorization_ref="env:FRED_API_KEY",
        params={"realtime_start": "2026-09-26"},
    )
    payload = request.as_dict()
    assert payload["source_id"] == "fred"
    assert payload["dataset"] == "series_observations"
    assert payload["authorization_ref"] == "env:FRED_API_KEY"


def test_source_result_rejects_unknown_quality_status():
    with pytest.raises(ValueError, match="quality_status"):
        SourceResult(None, [], {}, "completed")


def test_factory_rejects_unlisted_url_before_network(tmp_path):
    router = SourceRouter.from_file(ROOT / "config/source_registry.yaml")
    profile = router.profiles["10jqka"]
    adapter = build_adapter("10jqka", profile, output_dir=tmp_path)
    request = build_request("10jqka", {"instrument_id": "000001"}, requested_url="https://untrusted.example/data")
    with pytest.raises(Exception, match="allowlist"):
        fetch_with_adapter(adapter, request)


def test_planned_source_is_explicitly_not_ready(tmp_path):
    router = SourceRouter.from_file(ROOT / "config/source_registry.yaml")
    profile = router.profiles["yahoo_finance"]
    adapter = build_adapter("yahoo_finance", profile, output_dir=tmp_path)
    with pytest.raises(AdapterNotReady, match="no executable slice"):
        fetch_with_adapter(adapter, build_request("yahoo_finance", {"instrument_id": "SPY"}))


def test_licensed_source_requires_authorization_reference(tmp_path):
    router = SourceRouter.from_file(ROOT / "config/source_registry.yaml")
    profile = router.profiles["wind"]
    adapter = build_adapter("wind", profile, output_dir=tmp_path)
    with pytest.raises(Exception, match="authorization_ref"):
        fetch_with_adapter(adapter, build_request("wind", {"instrument_id": "SPY"}))


def test_dataset_contract_rejects_undeclared_endpoint():
    with pytest.raises(AdapterNotReady, match="undeclared dataset"):
        build_request("sec_edgar", {"dataset": "insider_trades", "cik": "0000320193"})


def test_maturity_counts_do_not_call_contract_only_sources_degraded_ready():
    report = adapter_status(ROOT / "config/source_registry.yaml")
    assert report["automatic_execution_count"] == 7
    assert report["degraded_execution_count"] == 0
    assert report["manual_review_only_count"] == 9
    assert report["blocked_count"] == 5
    ten = next(row for row in report["profiles"] if row["source_id"] == "10jqka")
    assert ten["automatic_execution_ready"] is True
    assert ten["authority_primary_allowed"] is False
    assert ten["cross_check_only"] is True


def test_replay_smoke_produces_snapshot_and_canonical_rows(tmp_path):
    result = replay("stats_gov_cn", "macro_series", ROOT / "tests/fixtures/http/stats_gov.json", "CPI", ROOT / "config/source_registry.yaml", tmp_path, {})
    assert result["status"] == "passed"
    assert result["rows"] == 1
    assert result["snapshot_hash"].startswith("sha256:")
    assert result["normalized_rows"][0]["point_in_time_status"] == "pass"
