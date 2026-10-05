from datetime import UTC, datetime

import pytest

from finahinking.data.user_api_contracts import (
    DataBatch,
    DataConnectionConfig,
    DataRequest,
    DataSourceCredentialRef,
)


def test_contracts_reject_secret_fields_and_unbounded_requests():
    config = DataConnectionConfig(
        connection_id="my-feed",
        display_name="My feed",
        base_url="https://example.test/data",
        credential_ref=DataSourceCredentialRef(env_var="FINAHINK_DATA_KEY"),
        auth_mode="bearer",
        field_mapping={"instrument": "ticker", "timestamp": "time", "close": "price"},
        records_path="data",
    )
    batch = DataBatch(
        records=({"instrument": "AAA", "timestamp": "2026-01-02T00:00:00Z", "close": 10.0},),
        connection_id=config.connection_id,
        retrieved_at=datetime.now(UTC),
        source_declaration="user supplied",
        data_fingerprint="a" * 64,
        quality_issues=(),
        pit_available="UNKNOWN",
    )
    assert "FINAHINK_DATA_KEY" not in repr(batch)
    public = batch.to_dict()
    assert "endpoint" not in public and "credential" not in str(public).lower()
    assert "/Users/" not in str(public)
    with pytest.raises(ValueError, match="bounded|maximum|limit"):
        DataRequest(dataset_kind="prices", instruments=tuple(f"S{i}" for i in range(1001)))
    with pytest.raises(ValueError, match="unsupported|auth"):
        DataConnectionConfig("x", "X", "https://example.test", None, "basic", {}, None)


def test_missing_available_at_remains_unknown():
    batch = DataBatch(
        records=({"instrument": "AAA", "timestamp": "2026-01-02T00:00:00Z", "close": 10.0},),
        connection_id="feed",
        retrieved_at=datetime.now(UTC),
        source_declaration="user declared",
        data_fingerprint="b" * 64,
        quality_issues=(),
        pit_available="UNKNOWN",
    )
    assert batch.pit_available == "UNKNOWN"
    assert batch.to_dict()["pit_available"] == "UNKNOWN"
