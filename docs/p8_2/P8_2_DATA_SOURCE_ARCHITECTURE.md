# Finathink P8.2 Data Source Architecture

**Status:** architecture and admission contract
**Date:** 2026-10-03 (Asia/Shanghai)

## Source principle

Finathink treats a source as a typed, inspectable evidence provider rather than
as a dataframe that happens to contain prices. Source identity, retrieval time,
time zone, as-of policy, license/terms, coverage, transformations, and
limitations travel with every observation and artifact.

The normalized boundary is:

```text
provider / fixture / bridge
  → SourceAdapter
  → MarketObservation(s)
  → DatasetSnapshot
  → feature/strategy/ML contracts
  → ResearchRun / QuantRun / chart view model
```

No UI route reads a provider-specific object directly. A source that cannot
produce a complete provenance record is not admitted as `LIVE` or `CAPTURED`.

## Source tiers and modes

| Mode | Meaning | Current P8.2 use | Required disclosure |
| --- | --- | --- | --- |
| `SAMPLE` | Deliberate deterministic product fixture | Chart/UI and offline tests | Fixture ID, synthetic/sample limitations, fingerprint |
| `CAPTURED` | Persisted response from a named source at a known time | Existing BLS evidence and future snapshots | Provider, source URL, retrieval timestamp, license/terms, revision status |
| `LIVE` | Fresh external response within an explicit freshness window | QMT only if a real bridge is separately connected | Connection state, retrieval time, stale threshold, source health |
| `SYNTHETIC` | Generated test data with no claim about markets | Performance and malformed-payload tests | Generation seed/method and “not market data” label |
| `PAPER` | Simulated output derived from historical/sample data | P6.6 paper research | Virtual clock, assumptions, no broker/live execution |

Labels are shown in text and machine-readable fields. A green chart or recent
timestamp never silently upgrades `SAMPLE` to `LIVE`.

## Canonical records

### Market observation

Each observation should contain a stable observation ID, instrument/symbol,
venue/market when known, timezone-aware timestamp, OHLCV (or a documented
subset), source adapter ID/version, source mode, availability/as-of metadata,
retrieval timestamp, and limitations. Numerical values must be finite and
consistent (`high >= max(open, close, low)`, `low <= min(open, close, high)` when
those fields are present); volume cannot be negative.

### Dataset snapshot

A snapshot is an ordered, bounded collection of observations plus:

- dataset ID and schema version;
- source/provider and source URL or local fixture reference;
- retrieval time and timezone policy;
- requested period and as-of cutoff;
- transformation/adjustment history;
- license/terms and redistribution status;
- row/column counts and deterministic fingerprint;
- known gaps, revisions, stale windows, and limitations.

Duplicate timestamps, out-of-order records, non-finite values, malformed
identifiers, and rows beyond the requested as-of boundary are rejected before
the snapshot can feed a research run.

### Events and features

Events use a canonical event ID, publication/effective timestamps, source,
revision status, and evidence links. Features carry definition/version,
inputs, lookback, computation timestamp/as-of policy, and lineage to the
source snapshot. A point inspector joins these records by canonical point ID;
it does not recompute them in the browser.

## Existing and planned adapters

### Local fixtures and captured sources

The repository already carries package fixtures under
`src/finahinking/_package_data/fixtures/`, including BLS CPI and quant/research
CSV examples. These are the first reliable offline path. The existing
`Provenance`/`Dataset` model and P6.5 temporal/evidence modules remain the
authority for source metadata and validation.

Fixture adapters must identify the exact file/fixture version and mark the
result `SAMPLE` or `CAPTURED`; they must not imply current market conditions.

### QMT / MiniQMT bridge (candidate B adapter)

The user logs in through the official QMT/MiniQMT client. Finathink may then
connect to a local or trusted-LAN bridge that exposes only bounded market-data
requests. A macOS Finathink process must not assume it can host a Windows-only
vendor client; a small Windows bridge is an explicit deployment boundary.

Proposed connection states:

```text
DISCONNECTED → LOGIN_REQUIRED → CONNECTING → CONNECTED
                       ↘ ERROR       ↘ STALE → DISCONNECTED
```

The bridge contract permits health/status and normalized market-data snapshots
only. It rejects broker passwords, account-control fields, order/cancel method
names, arbitrary URLs, unbounded symbol/period requests, and unauthenticated
non-loopback access. A token, when configured, is explicit and short-lived;
Finathink stores token fingerprints/state, not token values.

QMT responses are normalized with vendor/source ID, request period, retrieval
time, timezone, adjustment mode, row count, and fingerprint. A disconnected or
stale result remains labeled and cannot feed a `LIVE` claim. No local QMT
connection was available at inventory time, so only mock/offline evidence can
be claimed in the local P8.2 gate until a supported host is separately
authorized.

### Future public providers

AkShare, Tushare, and other providers remain pending admission. Before use,
each needs a source/terms review, rate-limit and key-handling design,
point-in-time/revision behavior, reproducible capture policy, and an adapter
test fixture. A package import alone is not source admission.

## Freshness, revisions, and PIT policy

The adapter records both event/publication time and retrieval time where the
source supplies them. Research queries use an explicit as-of cutoff; later
revisions cannot silently enter an earlier run. Corporate-action adjustments,
timezone conversion, resampling, missing bars, and session calendars are
recorded as transformations with their own fingerprint.

Features and labels are generated only from information available at the
feature timestamp. Train/validation/OOS split metadata references the same
dataset fingerprint and as-of policy. If the source cannot establish that
boundary, the result is `LIMITED`/`UNVERIFIED`, not a valid OOS claim.

## Data-health and UI contract

The data-source settings surface shows, for each source:

- trust/admission tier;
- mode and connection state;
- coverage/instrument/period;
- last refresh/retrieval and stale threshold;
- row count, missingness, and revision status;
- source URL/license/terms summary;
- limitations and a safe recovery action.

The research chart displays source mode and fingerprint near the chart/table,
and the selected-point inspector exposes timestamp, source, feature lineage,
event evidence, and limitations. The UI never displays credentials or vendor
raw objects.

## Failure semantics

| Failure | Canonical response | Persistence/UI behavior |
| --- | --- | --- |
| Provider unavailable | `DATA_UNAVAILABLE` with adapter/source reason | Show unavailable; use fixture only if explicitly selected |
| Provider returns no rows | `NO_DATA_AVAILABLE` | Empty state; do not fabricate values |
| Stale snapshot | `STALE` with freshness details | Keep visible but never label live |
| Revision/as-of ambiguity | `PIT_UNVERIFIED` | Block valid research/OOS artifact |
| Invalid row/duplicate/order | `INVALID_DATASET` | Return structured error; persist no partial snapshot |
| QMT disconnected | `DISCONNECTED` | Offer reconnect/status; retain no broker secret |

## Data-source verification

P8.2 source gates cover fixture determinism, provenance round trips,
chronological/PIT validation, mode labels, malformed QMT payloads, bounded
requests, disconnect/stale transitions, and fingerprint reproducibility. The
final report must distinguish source-adapter tests from an actual QMT host
connection; the former does not prove the latter.
