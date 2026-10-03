# Finathink P8.2 Capability Expansion Design

**Status:** approved execution brief derived from the user-supplied P8.2 mission  
**Date:** 2026-10-03 (Asia/Shanghai)

## Goal

Turn the local Finathink research surface into a serious, inspectable
quant-research workspace while preserving Finathink-owned contracts,
point-in-time and provenance boundaries, local-first operation, and the
research-only/no-live-execution rule.

## User intent and non-negotiables

- The P8.2 mission is the active request; P8.2B must not start until this
  phase has a final validation report.
- Computer Use is forbidden. All inspection, editing, testing, and package
  work uses shell, repository tools, official documentation, and headless
  automation only.
- Third-party projects are replaceable capability providers. They never own
  `ResearchRun`, `QuantRun`, `FeatureDefinition`, `StrategySpec`, provenance,
  or the Finathink UI vocabulary.
- QMT is data-only and read-only. Finathink never collects broker passwords and
  never exposes order, cancel, account-control, or real-money actions.
- Qlib and vectorbt remain isolated optional research sandboxes. The core app
  starts and tests without either package.
- Sample, captured, synthetic, paper, and live states are explicit; no chart
  or metric is allowed to imply a real source when it is fixture data.
- Every numerical output carries source, timestamp/period, method, lineage,
  fingerprint, uncertainty/limitations, and an inspectable artifact boundary.

## Recommended architecture

```text
source / fixture / QMT bridge
        ↓ typed provider adapter
Finathink MarketObservation + DatasetSnapshot
        ↓ feature / strategy / ML contracts
ResearchRun + QuantRun + Artifact + provenance/fingerprint
        ↓ normalized JSON view models
server-rendered shell + local static chart bundle
        ↓ user interaction
chart point → feature/event/strategy inspector → math/code/evidence
```

The first UI renderer is a locally bundled, dependency-pinned visualization
layer: Lightweight Charts for time-series navigation and ECharts for research
panels. A small Finathink-owned controller translates normalized JSON into
chart series and accessible selected-point tables. React Flow and TanStack
Table are evaluated but not required for the first slice; their absence must
produce a visible capability state rather than a broken page.

## Capability slices

### Slice A — reference and capability evidence

Audit the existing TradingAgents checkout and official Qlib/vectorbt metadata;
record classification, license, environment, security concerns, and fallback
in `docs/p8_2/`. No reference repository is vendored into `src/`.

### Slice B — Finathink research contracts

Add typed, JSON-safe contracts for `MarketObservation`, `DatasetSnapshot`,
`FeatureObservation`, `ResearchPoint`, `ParameterSweepSpecification`,
`SweepResult`, `MLResearchSpecification`, and QMT connection/health state.
Contracts validate identifiers, timestamps, finite numbers, point-in-time
availability, bounded payloads, and deterministic fingerprints.

### Slice C — adapters and graceful fallback

Implement a deterministic market fixture adapter and a read-only QMT bridge
adapter interface with an offline/mock implementation. Implement a simple
Finathink-native parameter sweep and an optional Qlib adapter boundary; no raw
external objects cross the boundary. Add a capability registry reporting
available/not-installed/not-connected states.

### Slice D — interactive research workspace

Add a research route with a normalized chart payload, a locally bundled chart
controller, selected-point inspector, accessible data table, feature/event
markers, and a compact parameter-sensitivity panel. The controller owns no
financial calculations; it renders server-produced values and emits selected
point IDs only.

### Slice E — validation and release evidence

Run full existing tests plus contract, adapter, chart-payload, headless
interaction, performance, security, dependency, notebook, packaging, and
governance gates. Record every optional dependency's exact state and stop
truthfully where Qlib, vectorbt, QMT, hosted deployment, or external CI are
unavailable.

## Data and interaction contract

The chart endpoint returns a bounded JSON document:

```json
{
  "schema_version": 1,
  "dataset": {"id": "...", "fingerprint": "...", "mode": "SAMPLE"},
  "points": [{"id": "...", "time": "...", "open": 0, "high": 0,
              "low": 0, "close": 0, "volume": 0,
              "features": {}, "events": [], "signal": null}],
  "features": [],
  "events": [],
  "limitations": []
}
```

The browser may sort, filter, highlight, and select a point but must not
recompute prices, returns, beta, feature values, signals, positions, ML
metrics, or backtest metrics. Keyboard selection and a plain table provide a
non-hover alternative for every chart fact.

## Error, fallback, and security behavior

- Missing optional capability → `NOT INSTALLED` / `NOT CONNECTED` card with a
  local fallback or clear next action.
- Invalid source/point payload → structured 400 with a recovery action; no
  partial result is persisted.
- QMT bridge defaults to loopback/read-only, validates an explicit token when
  configured, bounds requests, and exposes no trading method names.
- Chart assets are same-origin and pinned; CSP allows only the local bundle,
  with no remote scripts or fonts.
- Generated/model code is never executed from user text. ML model selection is
  allow-listed and sandboxed.

## Success criteria for P8.2

1. A user can open the research workspace, inspect a real normalized fixture,
   hover/select a timestamp, and see price/features/events/provenance in the
   inspector and accessible table.
2. A parameter sweep shows all experiments, OOS context, robustness/unstable
   regions, and multiple-testing warnings without a “best strategy” claim.
3. Capability settings expose internal engine, Qlib, vectorbt, QMT, and chart
   renderer states; absence of optional tooling does not crash core routes.
4. Core tests, packaging, and security gates remain green without optional
   Qlib/vectorbt/QMT installations.
5. Required P8.2 documents and a final validation report truthfully separate
   completed local work from deferred external/public gates.

## Explicitly deferred from this phase

Real-time QMT connectivity on an actual Windows host, broker/account data,
live orders, hosted multi-user auth, a public deployment, deep-learning models,
and automatic model/strategy selection require separate approvals and remain
out of scope for the P8.2 local stop condition.
