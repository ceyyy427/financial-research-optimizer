"""Capability and read-only QMT boundary tests."""

from __future__ import annotations

import pytest

from finahinking.p8_2.capabilities import CapabilityRegistry
from finahinking.p8_2.data_sources import FixtureMarketDataSource
from finahinking.p8_2.qmt import QMTBridgeClient, QMTConnectionState


def test_capability_detection_is_absent_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    registry = CapabilityRegistry.detect()
    assert registry.status("qlib") == "NOT INSTALLED"
    assert registry.status("vectorbt") == "NOT INSTALLED"
    assert registry.status("qmt") == "NOT CONNECTED"
    assert registry.to_dict()["qlib"]["status"] == "NOT INSTALLED"


def test_fixture_source_has_deterministic_provenance_and_pit_snapshot() -> None:
    source = FixtureMarketDataSource()
    first = source.snapshot()
    second = source.snapshot()
    assert first.fingerprint == second.fingerprint
    assert first.mode == "SAMPLE"
    assert first.pit_available(first.as_of) is True
    assert first.observations


def test_qmt_client_is_read_only_and_enforces_loopback_token_and_credentials() -> None:
    client = QMTBridgeClient(token="bridge-token")
    assert client.status().state is QMTConnectionState.NOT_CONFIGURED
    with pytest.raises(PermissionError):
        client.connect(token="wrong")
    client.connect(token="bridge-token")
    assert client.status().state is QMTConnectionState.CONNECTED_READ_ONLY
    snapshot = client.snapshot("DEMO", limit=3, token="bridge-token")
    assert snapshot.observations
    assert not hasattr(client, "order_stock")
    assert not hasattr(client, "cancel_order")
    with pytest.raises(ValueError, match="credential"):
        QMTBridgeClient(password="do-not-accept")
    with pytest.raises(PermissionError):
        client.snapshot("DEMO", token="wrong")
    client.disconnect()
    assert client.status().state is QMTConnectionState.DISCONNECTED


def test_qmt_rejects_non_loopback_hosts_by_default() -> None:
    with pytest.raises(ValueError, match="loopback"):
        QMTBridgeClient(host="192.0.2.10")


def test_qmt_trusted_lan_requires_authentication_token() -> None:
    with pytest.raises(ValueError, match="authentication token"):
        QMTBridgeClient(host="192.0.2.10", allow_trusted_lan=True)
    client = QMTBridgeClient(
        host="192.0.2.10", allow_trusted_lan=True, token="trusted-lan-token"
    )
    client.connect(token="trusted-lan-token")
    assert client.status().read_only is True


def test_qmt_normalizer_rejects_case_variant_trading_fields() -> None:
    from finahinking.p8_2.qmt import normalize_qmt_observation

    with pytest.raises(ValueError, match="trading"):
        normalize_qmt_observation({"ORDER_STOCK": True})
