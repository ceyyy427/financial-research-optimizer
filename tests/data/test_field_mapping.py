from finahinking.data.field_mapping import normalize_records


def test_normalize_records_maps_user_fields_and_reports_quality_issues():
    batch = normalize_records(
        [
            {"ticker": "AAA", "time": "2026-01-02T00:00:00Z", "price": "10.5", "volume": "bad"},
            {"ticker": "BBB", "time": "not-a-time", "price": "11"},
            {"ticker": "CCC", "time": "2026-01-03T00:00:00Z"},
        ],
        {"instrument": "ticker", "timestamp": "time", "close": "price", "volume": "volume"},
        "prices",
    )
    assert batch.records[0]["instrument"] == "AAA"
    assert batch.records[0]["close"] == 10.5
    assert any("volume" in issue for issue in batch.quality_issues)
    assert any("timestamp" in issue for issue in batch.quality_issues)
    assert any("close" in issue for issue in batch.quality_issues)


def test_normalize_records_preserves_unknown_pit_when_available_at_is_missing():
    batch = normalize_records(
        [{"ticker": "AAA", "time": "2026-01-02", "price": 10}],
        {"instrument": "ticker", "timestamp": "time", "close": "price"},
        "prices",
    )
    assert batch.pit_available == "UNKNOWN"
