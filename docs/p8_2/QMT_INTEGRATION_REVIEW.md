# QMT Integration Review

**Classification:** B — production adapter candidate, market-data only
**Review status:** architecture/mock boundary reviewed; vendor integration
unverified
**Review date:** 2026-10-03 (Asia/Shanghai)

## Scope and evidence

This review covers the proposed QMT/MiniQMT/`xtquant` boundary, not a claim of
vendor support. The local inspection found no QMT/MiniQMT process, no
`xtquant` module, no authenticated client, and no supported Windows bridge.
Vendor license/redistribution terms and API version were not verified. No
installation or login attempt was made.

The local implementation is a Finathink-owned mock/normalization seam in
`src/finahinking/p8_2/qmt.py`; it uses the deterministic fixture provider for
offline tests and intentionally does not import vendor code.

## Intended topology

```text
User → official QMT/MiniQMT client login (outside Finathink)
                         │
                 read-only local bridge
                         │
        bounded health + market-data snapshot API
                         │
              Finathink QMTBridgeClient
                         │
       MarketObservation / DatasetSnapshot / provenance
```

QMT may require a Windows host while Finathink currently runs on macOS. The
bridge host is therefore a separate, explicitly approved deployment surface;
Finathink must not silently emulate or embed the vendor client.

## Connection states and data path

The proposed state model distinguishes not configured, client missing/not
running, login required, connecting, read-only connected, syncing, ready,
degraded, and disconnected. A state transition never grants trading rights.

The adapter accepts bounded instrument/period requests and normalizes common
XtData-like fields into Finathink records. A real integration must additionally
provide exchange timezone, adjustment mode, session calendar, source coverage,
retrieval time, revision policy, freshness threshold, and a reproducible
response fingerprint before a source can be labeled `LIVE`. If subscriptions or
tick/quote data are later admitted, their permission and lifecycle must be
separate from the historical snapshot contract.

## Security decision

The user authenticates only in the official QMT client. Finathink stores no
broker password, account password, or session secret. A bridge token may be
configured and is retained only as a digest for comparison. Default binding is
loopback; trusted-LAN exposure requires an explicit opt-in, an authentication
token, and a separate security review.

The adapter surface excludes `order_stock`, `cancel_order`, account controls,
subscriptions that expose account state, and any real-money execution method.
The UI exposes read-only/data-health status and no login, order, cancel, or
portfolio-control actions.

## Local evidence

The focused P8.2 QMT tests cover:

- absent-safe capability state (`NOT CONNECTED`);
- token mismatch and successful mock connection;
- trusted-LAN token requirement;
- loopback enforcement;
- bounded snapshot requests;
- credential rejection;
- fixture normalization and deterministic provenance;
- disconnect state;
- absence of known trading methods.

These tests pass locally as part of the current focused P8.2 slice. They do
not prove vendor compatibility, market-data correctness, Windows deployment,
network security, or live latency.

## Admission checklist

Before changing the state from candidate to admitted, require all of the
following:

1. Vendor/API/version and license/terms review by the project owner.
2. Supported-host bridge with authentication, firewall/trusted-LAN policy,
   token rotation, redacted logs, and bounded request quotas.
3. Captured, licensed, replayable fixture covering bars, gaps, revisions,
   timezone/adjustment modes, and stale/disconnect transitions.
4. PIT/as-of, duplicate/order, finite-value, and fingerprint validation before
   any ResearchRun/QuantRun persistence.
5. Independent security review proving no credential or trading-method leak.
6. Core clean-install test with the bridge absent and an explicit offline
   fallback.
7. UI acceptance showing `LIVE` only when the bridge supplies fresh, verified
   data and otherwise showing `LOGIN REQUIRED`, `STALE`, or `NOT CONNECTED`.

Until this checklist passes, QMT remains a read-only candidate and the local
fixture/mock path is the only validated source.
