import json

from online.fred_alfred import FredAlfredProvider
from online.http_cache import HttpCache
from online.snapshot_store import SnapshotStore
from monitoring.freshness import check_freshness


def test_provider_cache_redacts_api_keys_and_saves_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("FRED_API_KEY", "secret-key")
    calls = []

    def transport(method, url, headers, timeout):
        calls.append(url)
        return 200, {"content-type": "application/json"}, b'{"observations": [{"date": "2026-09-25", "value": "1.2"}]}'

    provider = FredAlfredProvider(
        cache=HttpCache(tmp_path / "cache", transport=transport),
        snapshot_store=SnapshotStore(tmp_path / "snapshots"),
    )
    first = provider.fetch_series("GDP", realtime_start="2026-01-01")
    second = provider.fetch_series("GDP", realtime_start="2026-01-01")
    assert len(calls) == 1
    assert "secret-key" not in first["response"].request_url
    assert second["response"].from_cache is True
    manifest = first["response"].snapshot
    assert manifest["response_hash"]
    assert manifest["raw_file"]
    assert manifest["request_params"]["api_key"] == "[REDACTED]"


def test_freshness_returns_fallback_for_stale_cache():
    result = check_freshness({"retrieved_at": "2026-09-26T00:00:00+00:00", "stale": True, "from_cache": True, "http_status": 200}, now="2026-09-26T02:00:00+00:00", max_age_minutes=30)
    assert result["status"] == "fallback"
    assert result["cache_status"] == "stale"
