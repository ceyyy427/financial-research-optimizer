import json
from pathlib import Path

import pytest

from adapters.base import AdapterError
from adapters.catalog import CatalogSourceAdapter
from adapters.stats_gov_cn import StatsGovCnAdapter
from scripts.normalize_observations import canonicalize_observation
from scripts.source_router import SourceRouter, SourceRoutingError
from scripts.source_snapshot import create_snapshot
from scripts.validate_source_registry import validate_registry
from parsers import parse


ROOT = Path(__file__).resolve().parents[1]


def test_registry_profiles_validate_and_route_alfred():
    result = validate_registry(ROOT / "config/source_registry.yaml", ROOT / "schemas/source_profile.schema.json")
    assert result["valid"] is True
    assert result["profile_count"] >= 16
    router = SourceRouter.from_file(ROOT / "config/source_registry.yaml")
    plan = router.resolve("美国 CPI 历史修订值", ["CPIAUCSL"], ["point_in_time", "vintage_data"])
    assert plan["source_plan"][0]["source_id"] == "alfred"
    assert "cached_snapshot" in plan["fallback_plan"]
    assert "material_price_conflict" in plan["blocking_rules"]
    executable = router.resolve("China official macro", ["CPI"], ["point_in_time"], require_executable=True)
    assert executable["source_plan"][0]["source_id"] in {"stats_gov_cn", "pbc", "sse", "szse", "sec_edgar", "alfred", "ecb_sdmx", "bis_sdmx"}


def test_router_rejects_missing_capability():
    router = SourceRouter.from_file(ROOT / "config/source_registry.yaml")
    with pytest.raises(SourceRoutingError):
        router.resolve("需要 point-in-time", ["SPY"], ["point_in_time", "vintage_data"], required_fields=["nonexistent_field"])


def test_snapshot_replay_is_immutable_and_hashes_raw_bytes(tmp_path):
    raw = tmp_path / "response.json"
    raw.write_bytes(b'{"value": 1}')
    manifest = create_snapshot("sse", raw, tmp_path / "snapshots", "https://www.sse.com.cn/data", content_type="application/json", parser_version="sse_v1", source_authority="exchange", point_in_time_status="pass", revision_status="release_aware")
    saved = Path(manifest["raw_file"])
    assert saved.read_bytes() == raw.read_bytes()
    assert manifest["snapshot_hash"].startswith("sha256")
    raw.write_bytes(b'{"value": 2}')
    replay = create_snapshot("sse", raw, tmp_path / "snapshots", "https://www.sse.com.cn/data", content_type="application/json", parser_version="sse_v1", source_authority="exchange", point_in_time_status="pass", revision_status="release_aware")
    assert replay["snapshot_hash"] != manifest["snapshot_hash"]


def test_canonical_observation_preserves_pit_fields_and_rejects_future_availability():
    profile = {"source_id": "sse", "authority": "exchange", "primary_method": "official_download", "point_in_time": True, "revision_aware": True, "parser": "sse_v1", "base_urls": ["https://www.sse.com.cn/"]}
    snapshot = {"snapshot_hash": "sha256:abc12345"}
    row = canonicalize_observation({"instrument_id": "600519", "field": "close", "value": 1450.2, "unit": "CNY", "observation_time": "2026-09-25T15:00:00+08:00", "release_time": "2026-09-25T15:05:00+08:00", "availability_time": "2026-09-25T15:05:00+08:00", "effective_time": "2026-09-25T15:00:00+08:00", "vintage_time": None, "source_url": "https://www.sse.com.cn/data"}, profile, snapshot)
    assert row["point_in_time_status"] == "pass"
    assert row["release_time"].endswith("+00:00")
    with pytest.raises(ValueError, match="availability_time"):
        canonicalize_observation({"instrument_id": "600519", "field": "close", "value": 1450.2, "observation_time": "2026-09-25T15:00:00+00:00", "availability_time": "2026-09-25T14:00:00+00:00", "effective_time": "2026-09-25T15:00:00+00:00"}, profile, snapshot)


def test_licensed_adapter_blocks_expired_login():
    profile = json.loads((ROOT / "examples/source_profile.json").read_text(encoding="utf-8"))
    profile.update({"source_id": "wind", "access_policy": "licensed_only", "authentication": {"required": True}})
    adapter = CatalogSourceAdapter(profile, authorization_status="expired")
    with pytest.raises(AdapterError, match="requires authorized access"):
        adapter.planned_request(topic="财务数据")


def test_stats_gov_adapter_fetches_snapshots_and_parses_records(tmp_path):
    profile = json.loads((ROOT / "examples/source_profile.json").read_text(encoding="utf-8"))
    profile.update({"source_id": "stats_gov_cn", "authority": "national_statistics", "parser": "stats_gov_json", "primary_method": "api", "point_in_time": True, "revision_aware": True, "base_urls": ["https://data.stats.gov.cn/"]})

    def transport(method, url, headers, timeout):
        return 200, {"content-type": "application/json"}, b'{"data": [{"indicator": "CPI", "date": "2026-08-01", "release_date": "2026-09-10T12:30:00Z", "value": 101.2, "unit": "%"}]}'

    adapter = StatsGovCnAdapter(profile, cache_dir=tmp_path / "cache", snapshot_dir=tmp_path / "snapshots", transport=transport)
    result = adapter.fetch("https://data.stats.gov.cn/api/cpi", instrument_id="CPI")
    assert len(result["observations"]) == 1
    assert result["snapshot"]["source_id"] == "stats_gov_cn"
    assert result["snapshot"]["snapshot_hash"].startswith("sha256:")


def test_offline_parser_fixture_replay(ROOT):
    payload = json.loads((ROOT / "tests/fixtures/http/stats_gov.json").read_text(encoding="utf-8"))
    rows = parse("stats_gov_json", payload, instrument_id="CPI", source_url="https://data.stats.gov.cn/")
    assert rows[0]["value"] == 101.2
    assert rows[0]["availability_time"] == "2026-09-10T12:30:00Z"
    ecb = parse("ecb_sdmx_json", (ROOT / "tests/fixtures/http/ecb_sdmx.csv").read_text(encoding="utf-8"), instrument_id="PCPI")
    assert ecb[0]["value"] == 101.2
