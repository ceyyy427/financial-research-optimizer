"""Read-only, credential-free QMT market-data bridge boundary.

The real QMT/XtData SDK is intentionally not imported here.  A future bridge
process can implement the tiny ``snapshot`` provider protocol and feed raw
records through :func:`normalize_qmt_observation`.
"""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from .contracts import DatasetSnapshot, MarketObservation
from .data_sources import FixtureMarketDataSource


class QMTConnectionState(str, Enum):
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CLIENT_NOT_FOUND = "CLIENT_NOT_FOUND"
    CLIENT_NOT_RUNNING = "CLIENT_NOT_RUNNING"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    CONNECTING = "CONNECTING"
    CONNECTED_READ_ONLY = "CONNECTED_READ_ONLY"
    DATA_SYNCING = "DATA_SYNCING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"


@dataclass(frozen=True)
class QMTStatus:
    state: QMTConnectionState
    host: str
    port: int
    read_only: bool = True
    client_running: bool = False
    login_ready: bool = False
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "host": self.host,
            "port": self.port,
            "read_only": self.read_only,
            "client_running": self.client_running,
            "login_ready": self.login_ready,
            "message": self.message,
        }


class QMTDataProvider(Protocol):
    def snapshot(self, instrument: str, *, limit: int = 256) -> DatasetSnapshot:
        """Return normalized observations; provider may be a bridge process."""


_CREDENTIAL_KEYS = {"password", "broker_password", "username", "account", "secret", "credential"}
_FORBIDDEN_METHODS = {"order_stock", "cancel_order", "subscribe_account", "query_account", "XtTrader"}
_FORBIDDEN_METHODS_CASEFOLD = {item.casefold() for item in _FORBIDDEN_METHODS}


def normalize_qmt_observation(raw: Mapping[str, Any] | object, *, provider: str = "qmt-xtdata", adapter_version: str = "p8.2-qmt-1") -> MarketObservation:
    """Normalize a raw XtData-like mapping without retaining provider objects."""

    if not isinstance(raw, Mapping):
        attributes = getattr(raw, "__dict__", None)
        if not isinstance(attributes, Mapping):
            raise TypeError("QMT observation must be a mapping-like record")
        raw = attributes
    if any(str(key).casefold() in _CREDENTIAL_KEYS for key in raw):
        raise ValueError("QMT credentials are not accepted")
    if any(str(key).casefold() in _FORBIDDEN_METHODS_CASEFOLD for key in raw):
        raise ValueError("QMT trading fields are not accepted")
    def pick(*names: str, default: Any = None) -> Any:
        for name in names:
            if name in raw:
                return raw[name]
        return default

    timestamp = pick("timestamp", "time", "datetime", "date")
    instrument = pick("instrument", "symbol", "stock_code", "ticker")
    if timestamp is None or instrument is None:
        raise ValueError("QMT observation requires instrument and timestamp")
    return MarketObservation(
        instrument=str(instrument),
        timestamp=timestamp,
        open=pick("open", "open_price"),
        high=pick("high", "high_price"),
        low=pick("low", "low_price"),
        close=pick("close", "close_price", "last_price"),
        volume=pick("volume", default=0.0),
        amount=pick("amount", "turnover"),
        source="qmt",
        provider=provider,
        retrieved_at=pick("retrieved_at", default=timestamp),
        available_at=pick("available_at", default=timestamp),
        adapter_version=adapter_version,
    )


class QMTBridgeClient:
    """A bounded mock/bridge client exposing market data only."""

    def __init__(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 0,
        token: str | None = None,
        provider: QMTDataProvider | None = None,
        allow_trusted_lan: bool = False,
        **kwargs: Any,
    ) -> None:
        credential_keys = {str(key).casefold() for key in kwargs}
        if credential_keys & _CREDENTIAL_KEYS:
            raise ValueError("QMT broker credential handling is outside Finathink")
        if not isinstance(host, str) or not host.strip():
            raise ValueError("QMT bridge host is required")
        host = host.strip()
        loopback = host in {"127.0.0.1", "localhost", "::1"}
        if not loopback and not allow_trusted_lan:
            raise ValueError("QMT bridge is loopback-only unless trusted LAN is explicitly enabled")
        if not loopback and token is None:
            raise ValueError("trusted-LAN QMT bridge requires an authentication token")
        if not isinstance(port, int) or isinstance(port, bool) or port < 0 or port > 65535:
            raise ValueError("QMT bridge port is invalid")
        if token is not None and (not isinstance(token, str) or not token or len(token) > 256):
            raise ValueError("QMT bridge token is invalid")
        self.host = host
        self.port = port
        self._token_digest = self._digest_token(token) if token is not None else None
        self._provider = provider or FixtureMarketDataSource(source_id="qmt-offline-fixture")
        self._state = QMTConnectionState.NOT_CONFIGURED
        self._token_required = token is not None
        self._connected = False
        self._authenticated = False

    @staticmethod
    def _digest_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _authorize(self, token: str | None) -> None:
        if not self._token_required:
            return
        if token is None and self._authenticated:
            return
        if token is None or not hmac.compare_digest(self._token_digest or "", self._digest_token(token)):
            raise PermissionError("QMT bridge token is invalid")

    def status(self) -> QMTStatus:
        return QMTStatus(
            state=self._state,
            host=self.host,
            port=self.port,
            read_only=True,
            client_running=self._connected,
            login_ready=self._connected,
            message="market-data-only bridge",
        )

    def connect(self, token: str | None = None) -> QMTStatus:
        self._authorize(token)
        self._state = QMTConnectionState.CONNECTING
        self._connected = True
        self._authenticated = True
        self._state = QMTConnectionState.CONNECTED_READ_ONLY
        return self.status()

    def disconnect(self) -> QMTStatus:
        self._connected = False
        self._authenticated = False
        self._state = QMTConnectionState.DISCONNECTED
        return self.status()

    def health(self) -> QMTStatus:
        """Read-only alias for integrations that call the bridge health check."""

        return self.status()

    def snapshot(self, instrument: str = "DEMO", *, limit: int = 256, token: str | None = None) -> DatasetSnapshot:
        self._authorize(token)
        if not self._connected:
            raise ConnectionError("QMT bridge is not connected")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 256:
            raise ValueError("QMT request limit must be between 1 and 256")
        self._state = QMTConnectionState.DATA_SYNCING
        try:
            result = self._provider.snapshot(instrument, limit=min(limit, 256))
            if isinstance(result, DatasetSnapshot):
                normalized = result
            elif isinstance(result, Mapping) and "observations" in result:
                raw_records = result["observations"]
                if not isinstance(raw_records, Sequence) or isinstance(raw_records, (str, bytes)):
                    raise TypeError("QMT provider observations must be a sequence")
                normalized_records = tuple(normalize_qmt_observation(item) for item in raw_records)
                normalized = DatasetSnapshot(
                    dataset_id=f"qmt-{instrument}",
                    observations=tuple(sorted(normalized_records, key=lambda item: (item.instrument, item.timestamp))),
                    mode="CAPTURED",
                    provenance={"provider": "qmt-xtdata", "source": "QMT bridge"},
                )
            elif isinstance(result, Sequence) and not isinstance(result, (str, bytes)):
                normalized_records = tuple(normalize_qmt_observation(item) for item in result)
                if not normalized_records:
                    raise ValueError("QMT provider returned no observations")
                normalized = DatasetSnapshot(
                    dataset_id=f"qmt-{instrument}",
                    observations=tuple(sorted(normalized_records, key=lambda item: (item.instrument, item.timestamp))),
                    mode="CAPTURED",
                    provenance={"provider": "qmt-xtdata", "source": "QMT bridge"},
                )
            else:
                raise TypeError("QMT provider must return DatasetSnapshot or normalized records")
            self._state = QMTConnectionState.READY
            return normalized
        except Exception:
            self._state = QMTConnectionState.DEGRADED
            raise


__all__ = ["QMTBridgeClient", "QMTConnectionState", "QMTStatus", "normalize_qmt_observation"]
