from __future__ import annotations

import json
from datetime import date

import pytest

from finahinking.data.connection_settings import (
    DataConnectionPersistenceError,
    InMemoryDataCredentialStore,
    PersistentDataConnectionStore,
)
from finahinking.data.user_api_contracts import DataConnectionConfig, DataSourceCredentialRef
from finahinking.research.contracts import FailureKind, ResearchPlan, ResearchRequest, ResearchState
from finahinking.research.workflow import ResearchOrchestrator


def _request() -> ResearchRequest:
    return ResearchRequest(
        run_id="connection-run",
        instrument="ETF:SPY",
        as_of=date(2026, 10, 1),
        research_plan=ResearchPlan(required_datasets=("prices",), factor_ids=("fixture.factor.v1",)),
        analyst_roles=("fundamentals",),
        asset_class="ETF",
        workflow_version="research.v1",
        config_digest="cfg",
    )


def test_persistent_connection_store_reopens_without_secret(tmp_path) -> None:
    credentials = InMemoryDataCredentialStore()
    path = tmp_path / "connections.json"
    config = DataConnectionConfig(
        connection_id="private-feed",
        display_name="Private feed",
        base_url="https://example.test/api",
        credential_ref=None,
        auth_mode="no_auth",
        field_mapping={"instrument": "ticker", "timestamp": "time", "close": "price"},
    )
    store = PersistentDataConnectionStore(path, credential_store=credentials)
    store.save(config)
    reopened = PersistentDataConnectionStore(path, credential_store=credentials)
    assert reopened.get("private-feed") == config
    assert "api_key" not in path.read_text()
    assert "super-secret" not in path.read_text()


def test_persistent_store_keeps_only_keychain_reference(tmp_path) -> None:
    credentials = InMemoryDataCredentialStore()
    path = tmp_path / "connections.json"
    ref = DataSourceCredentialRef(keychain_label="finathink-data-opaque")
    config = DataConnectionConfig(
        connection_id="private-feed",
        display_name="Private feed",
        base_url="https://example.test/api",
        credential_ref=ref,
        auth_mode="bearer",
        field_mapping={"instrument": "ticker", "timestamp": "time", "close": "price"},
    )
    PersistentDataConnectionStore(path, credential_store=credentials).save(config, credential_value="super-secret")
    contents = path.read_text()
    assert "super-secret" not in contents
    assert "keychain_label" in contents and "finathink-data-opaque" in contents


def test_research_entrypoint_missing_connection_is_typed_and_does_not_download(tmp_path) -> None:
    store = PersistentDataConnectionStore(tmp_path / "connections.json", credential_store=InMemoryDataCredentialStore())
    result = ResearchOrchestrator(connection_store=store).run_from_connection("missing", _request())
    assert result.state.current_state is ResearchState.DATA_UNAVAILABLE
    assert result.state.failure_kind is FailureKind.DATA_UNAVAILABLE
    assert result.decision is None


@pytest.mark.parametrize(
    "payload",
    [None, [], "text", {"connections": [None]}, {"schema_version": 2, "connections": []}],
)
def test_persistent_store_rejects_malformed_or_unsupported_documents(tmp_path, payload) -> None:
    path = tmp_path / "connections.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(DataConnectionPersistenceError, match="invalid"):
        PersistentDataConnectionStore(path, credential_store=InMemoryDataCredentialStore())


def test_persistent_store_flush_failure_keeps_memory_and_disk_consistent(tmp_path, monkeypatch) -> None:
    path = tmp_path / "connections.json"
    store = PersistentDataConnectionStore(path, credential_store=InMemoryDataCredentialStore())
    original = DataConnectionConfig(
        connection_id="feed",
        display_name="Original",
        base_url="https://example.test/api",
        credential_ref=None,
        auth_mode="no_auth",
        field_mapping={},
    )
    store.save(original)
    replacement = DataConnectionConfig(
        connection_id="feed",
        display_name="Replacement",
        base_url="https://example.test/other",
        credential_ref=None,
        auth_mode="no_auth",
        field_mapping={},
    )
    monkeypatch.setattr("finahinking.data.connection_settings.os.replace", lambda *args: (_ for _ in ()).throw(OSError("denied")))
    with pytest.raises(DataConnectionPersistenceError, match="persistence"):
        store.save(replacement)
    assert store.get("feed") == original
    assert "Original" in path.read_text()
    assert "Replacement" not in path.read_text()
