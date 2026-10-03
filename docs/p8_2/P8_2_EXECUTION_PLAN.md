# Finathink P8.2 Execution Plan

**Phase:** P8.2 — Capability Expansion, Quant Research Platform, QMT Data
Bridge, and Visualization Rebuild
**Plan status:** active, local-first execution plan
**Plan date:** 2026-10-03 (Asia/Shanghai)
**Authority:** the user-supplied P8.2 Mission v1.0, the approved design brief
and the implementation plan in
`docs/superpowers/plans/2026-10-03-finathink-p82-capability-expansion.md`.

This document is a work order and gate record. It is not a claim that every
stage below has passed. The final validation report must replace each
`PLANNED`/`IN PROGRESS` state with evidence or an explicit blocker.

## Objective and stop condition

P8.2 makes the local Finathink application an inspectable research workspace:
financial series, features, events, parameter studies, ML research, paper
research, provenance, and learning remain connected without giving a
third-party library ownership of Finathink's domain model.

The phase stops at a truthful P8.2 final validation report and a local
validated checkpoint. P8.2B must not start in this phase. In particular, a
green local gate does not authorize live trading, broker control, hosted
deployment, or a public release.

## Non-negotiable boundaries

- Computer Use is forbidden for this mission. Repository-native tools, shell,
  official metadata, and headless tests are the allowed inspection paths.
- `ResearchRun`, `QuantRun`, feature/strategy definitions, provenance,
  point-in-time (PIT) policy, and UI vocabulary are Finathink-owned.
- QMT is a market-data bridge only. No broker password is collected or stored;
  no order, cancel, account-control, or real-money method is exposed.
- Qlib and vectorbt are optional isolated sandboxes. The core app and core
  tests must work when both packages are absent.
- Every result identifies its data mode (`LIVE`, `CAPTURED`, `SAMPLE`,
  `SYNTHETIC`, or `PAPER`), source, retrieval/as-of information, method,
  fingerprint, uncertainty, and limitations.
- Browser code renders normalized server values and emits selection events. It
  does not calculate prices, returns, signals, features, ML metrics, or
  backtest metrics.
- No external repository is vendored into `src/`; no raw Qlib, vectorbt, or
  QMT object crosses an adapter boundary.

## Baseline and evidence posture

The last local P8.1 validation tag is `p8-1-local-validated` at commit
`3ad75dca9ef1c3cf0eb5ec41b6d1a4c4b0846501`. The P8.2 design/spec checkpoint
is commit `13f4805573bcc0db0962a0298baa726d5b76229f`. These are local Git
facts; the canonical GitHub history is unrelated and must not be treated as a
merge or publication target without a separately verified common ancestor.

At plan authoring time, the following evidence is available:

| Area | State | Evidence / limitation |
| --- | --- | --- |
| Reference audit | `COMPLETE` | TradingAgents, Qlib, vectorbt records in `docs/p8_2/`; read-only inspection only |
| Skill inventory | `COMPLETE` | 161 `SKILL.md` files discovered across configured roots; selected skills recorded in `P8_2_CAPABILITY_MATRIX.md` |
| Domain contracts/adapters | `LOCAL VALIDATED` | Finathink-owned contracts, deterministic fallback, and focused tests pass; provider admission remains separate |
| Local chart bundle | `LOCAL VALIDATED / BROWSER DEFERRED` | Pinned frontend workspace, schema/normalization tests, static fallback table, and build pass; no browser binary is available for DOM/E2E evidence |
| Qlib | `ISOLATED SMOKE PASS; ADMISSION DEFERRED` | Native macOS arm64 Python 3.12 `.venv-qlib-py312` now passes `pyqlib==0.9.7` import/LightGBM OOS smoke and `pip check`; provider/PIT admission remains deferred |
| vectorbt | `CORE NOT INSTALLED; SANDBOX SMOKE PASS` | `.venv-vectorbt` is isolated with vectorbt 1.1.1; Commons Clause/legal admission remains open |
| QMT | `NOT CONNECTED` | No `xtquant`/QMT process or client was found locally; mock/offline behavior is the local gate |
| Public/remote release | `DEFERRED` | No push, merge, or public-release claim belongs to P8.2 local validation |

## Ordered work stages

### Stage A — reference and capability evidence (`COMPLETE`)

1. Inventory all available skills and capability providers.
2. Audit the local TradingAgents checkout and official Qlib/vectorbt metadata.
3. Record versions, licenses, Python constraints, dependency risks, and
   fallback decisions.
4. Classify every external project as A (core), B (production adapter), C
   (optional sandbox), D (reference laboratory), or E (rejected/deferred).

Exit gate: reference documents exist, no reference source is imported by the
core package, and no unverified tool is described as available.

### Stage B — visualization foundation

1. Pin the local frontend build inputs (Lightweight Charts for time series,
   ECharts for research panels, esbuild for bundling).
2. Build a normalized chart payload with bounded point count, chronological
   validation, feature/event metadata, source mode, and dataset fingerprint.
3. Implement crosshair, zoom/pan, markers, selected-point inspection, and an
   accessible table fallback.
4. Keep chart calculations server-side and keep chart assets same-origin.

Exit gate: headless tests prove malformed/duplicate/out-of-order payloads are
rejected; point selection emits only a canonical point ID; no remote script or
font is required; the route remains usable with JavaScript disabled.

### Stage C — Finathink research contracts

1. Add immutable JSON-safe records for observations, dataset snapshots,
   feature observations, research points, sweeps, ML specifications/results,
   capabilities, and QMT connection state.
2. Validate identifiers, finite numbers, timestamps, payload bounds, PIT
   availability, and forbidden executable/credential fields.
3. Generate deterministic fingerprints from canonical JSON and preserve
   lineage through every adapter.

Exit gate: focused contract tests cover round trips, invalid values,
fingerprint changes, and PIT violations; full existing tests remain green.

### Stage D — internal research engine and optional adapters

1. Use Finathink's existing quant/research runtime as the authoritative
   fallback.
2. Implement a deterministic parameter sweep that records every cell, train/
   validation/OOS context, robustness/instability regions, and multiple-
   testing warnings. It must not emit a “best strategy” conclusion.
3. Expose a typed Qlib adapter seam and a deterministic fallback. If a future
   Python 3.12 sandbox is admitted, run only a small licensed fixture and
   normalize its output to Finathink records.
4. Keep vectorbt behind a separate adapter and environment. Its license and
   all optional extras require review before distribution or hosting.

Exit gate: adapter absence produces an explicit capability state and local
fallback; no raw third-party object appears in serialized Finathink output.

### Stage E — QMT data bridge

1. Implement a read-only interface and offline/mock provider first.
2. Model `LOGIN_REQUIRED`, `CONNECTED`, `STALE`, `DISCONNECTED`, and
   `ERROR` states separately from data availability.
3. Treat a Windows QMT/MiniQMT host as a possible external bridge; the local
   macOS process must not assume it can host the vendor client.
4. Normalize OHLCV/events into Finathink records with source, retrieval time,
   as-of policy, timezone, and fingerprint.

Exit gate: token/host checks, bounded requests, credential rejection,
disconnect, stale-data handling, and forbidden trading-method tests pass.

### Stage F — product surfaces and settings

Provide total routes for the research workspace, ML Lab, Parameter Lab,
research history, research-engine settings, and data-source settings. Every
optional absence is visible as `NOT INSTALLED` or `NOT CONNECTED`; no missing
package may crash the home or research route.

The UI must preserve the existing local shell's accessibility rules: visible
focus, keyboard selection, text labels in addition to color, reduced-motion
support, responsive layout, and a plain data-table alternative to hover-only
facts.

### Stage G — final audit and stop

Run the complete existing suite plus P8.2 tests, frontend build/test, chart
interaction and payload-performance smoke, adapter/QMT mock tests, Ruff,
governance, notebook, pip checks, dependency audit, clean install, secret
scan, and `git diff --check`. Record exact commands and outputs in
`P8_2_FINAL_VALIDATION_REPORT.md`.

The final report must identify local commit/worktree state, every optional
environment's actual state, and all external/public gates that remain
unverified. Only after the human reviews this report may a later phase open
P8.2B.

## Gate matrix

| Gate | Required evidence | Failure action |
| --- | --- | --- |
| Contracts | Focused tests, JSON round trips, deterministic fingerprints | Do not expose route or adapter output |
| Data quality | PIT/order/duplicate/finite-value tests and source labels | Reject payload; preserve no partial artifact |
| Research validity | OOS boundary, cost/slippage assumptions, multiple-testing metadata | Mark result invalid/limited; never promote a winner |
| Visualization | Node/headless tests, local asset/CSP checks, table fallback | Keep route in fallback mode; no remote assets |
| Optional engines | Isolated import/smoke evidence, exact versions, license record | Per-engine state (`NOT INSTALLED` or `SMOKE PASS`); internal fallback remains |
| QMT | Offline/mock tests, auth boundary, read-only method audit | `NOT CONNECTED`; no vendor credentials or trading API |
| Security | secret scan, generated-code audit, dependency and CSP review | Block release and remove unsafe path |
| Performance | 1k/10k payload and interaction measurements | Bound payload or defer feature |
| Packaging | clean install, package-data check, pip check, diff check | Keep local checkpoint unvalidated |

## Required deliverables

The final P8.2 tree must contain the mission-required architecture, review,
adapter, sandbox, UI, performance, security, and validation documents under
`docs/p8_2/`, including this plan, the capability matrix, dependency topology,
and `P8_2_FINAL_VALIDATION_REPORT.md`. A document may say `DEFERRED` or
`NOT VERIFIED`, but it must include the exact reason and recovery condition.

## Safe recovery rules

- If an optional package conflicts with core dependencies, remove it from the
  optional environment rather than changing the core lock.
- If an external source is unavailable or terms are unclear, retain the
  fixture/offline adapter and label the result; do not synthesize “live” data.
- If a route receives an invalid payload, return a structured client error and
  do not persist a partial `ResearchRun`/artifact.
- If a gate cannot be run locally, report it as unverified. A green neighboring
  test does not substitute for missing evidence.
