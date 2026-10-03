# Finathink P8.2 QMT Bridge Contract

**Status:** read-only mock/adapter boundary implemented; real QMT connection
not verified
**Date:** 2026-10-03 (Asia/Shanghai)

## Scope

QMT/MiniQMT is a candidate **B — production adapter** for market data only.
Finathink does not become a QMT client, broker terminal, or execution engine.
The user remains authenticated in the official QMT client; a future bridge may
expose a bounded, authenticated snapshot endpoint to Finathink.

The current implementation intentionally does not import `xtquant` or any
vendor SDK. It provides a mock/offline bridge in `src/finahinking/p8_2/qmt.py`
and a deterministic fixture provider for tests.

## Platform topology

```text
Official QMT/MiniQMT client (possible Windows host)
       │ user login remains here
       ▼
Minimal read-only bridge (loopback or explicitly trusted LAN)
       │ bounded token-authenticated snapshot/health calls
       ▼
Finathink QMTBridgeClient (macOS/local app)
       │ normalize and validate
       ▼
MarketObservation → DatasetSnapshot → ResearchRun/UI
```

The local macOS runtime must not assume that a Windows-only QMT process can be
hosted in-process. The bridge is an explicit deployment boundary and remains
optional; the core app starts without it.

## Implemented contract

`QMTBridgeClient` exposes only:

- `status()` / `health()`;
- `connect(token=...)`;
- `disconnect()`;
- bounded `snapshot(instrument, limit, token=...)`.

`QMTConnectionState` distinguishes `NOT_CONFIGURED`, client/login/connect
states, `CONNECTED_READ_ONLY`, `DATA_SYNCING`, `READY`, `DEGRADED`, and
`DISCONNECTED`. Status records include host, port, read-only flag, client and
login booleans, and a non-secret message.

The constructor defaults to loopback (`127.0.0.1`, port 0). Non-loopback hosts
require an explicit trusted-LAN flag **and** an authentication token. The token
is stored only as a SHA-256 digest and compared with `hmac.compare_digest`;
token values are not serialized or logged. Request limits are bounded to 1–256
observations.

The bridge rejects credential-like constructor/record keys (`password`,
`broker_password`, `username`, `account`, `secret`, `credential`) and keeps
order/cancel/account method names outside its public surface. Raw mapping-like
records are normalized to `MarketObservation`; provider objects do not cross
the boundary.

## Normalization fields

The adapter maps common XtData-like aliases (`symbol`/`stock_code`,
`datetime`/`date`, `open_price`, `last_price`, `turnover`) into:

- instrument and timezone-aware timestamp;
- OHLCV and optional amount;
- source `qmt`, provider/adapter version;
- retrieval and availability timestamps;
- normalized `DatasetSnapshot` mode, provenance, and fingerprint.

The resulting snapshot is the only form that may enter feature, strategy, ML,
chart, or research-history code. Adjustment mode, exchange timezone, requested
period, row count, freshness, and source terms must be added by a real bridge
before a connected source can be labeled `LIVE`.

## Connection and data-health UI

The current settings surfaces expose `/settings/engines` and
`/settings/data-sources`, plus `/api/research/qmt`. They display explicit
read-only state, host/port metadata, and denied operations. They do not render
login forms, broker passwords, order buttons, account controls, or a false
connected state. A disconnected/stale snapshot remains labeled and cannot be
promoted to live evidence.

An admitted bridge should extend the data-source card with market-data
permissions, historical coverage, subscription status, last update/freshness,
data health, and local storage state. The current offline card intentionally
shows only the safe connection boundary; these coverage/subscription fields
are not evidence of a live QMT connection.

## Failure and recovery contract

| Condition | Response | Recovery |
| --- | --- | --- |
| No bridge configured | `NOT_CONFIGURED`/`NOT CONNECTED` | Start approved bridge, then reconnect |
| Wrong/missing token | `PermissionError` | Reconfigure explicit bridge token; do not ask for broker password |
| Non-loopback host without opt-in | `ValueError` | Use loopback or an explicitly reviewed trusted-LAN deployment |
| Limit outside 1–256 | `ValueError` | Narrow the request |
| Invalid/credential/trading record | `ValueError` | Remove unsafe fields; request normalized market data only |
| Provider failure | `DEGRADED` state and raised error | Preserve reason; use fixture/offline source |
| Disconnect | `DISCONNECTED` | Reconnect through official client/bridge |

No partial `DatasetSnapshot` or research artifact should be persisted after a
normalization failure.

## Evidence and unverified items

The focused QMT/capability tests pass as part of the current 19-test P8.2
Python slice, covering token checks, loopback enforcement, credential
rejection, trusted-LAN token enforcement, fixture snapshot,
connection/disconnect, and absence of known trading methods. No QMT/MiniQMT process, `xtquant` module, vendor client,
Windows host, or real market-data connection was found locally. Therefore this
document does not claim live QMT integration, vendor compatibility, latency,
or redistribution rights.

Before admission as a production adapter, add a supported-host smoke test,
vendor terms/license review, certificate/token rotation plan, replayable
captured fixture, stale/revision/PIT checks, and an independent security
review. The bridge remains `NOT CONNECTED` until those gates pass.
