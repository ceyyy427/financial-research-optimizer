# Finathink P8.2 Final Validation Report

**Date:** 2026-10-03 (Asia/Shanghai)
**Phase:** P8.2 — Capability Expansion / Quant Research Platform
**Decision:** CONDITIONAL LOCAL VALIDATION; STOP FOR HUMAN REVIEW
**Computer Use:** NOT USED (the mission explicitly forbids it, and the user
also requested that it not be used)

## 1. Scope and stop decision

P8.2 is complete to a deliberately conditional, local-first checkpoint. The
implementation extends the existing Finathink-owned research and education
contracts without making an external quant library, broker SDK, browser
renderer, or remote repository the source of truth.

P8.2B has **not started**. No P8.2B source files, dependencies, gates, or
remote actions were created. The next action is human review of this report
and the local checkpoint; P8.2B may only be opened after that review.

## 2. Delivered local capability

- Added immutable, JSON-safe P8.2 contracts for market observations, dataset
  snapshots, research points, feature observations, ML specifications/results,
  parameter sweeps, provenance, fingerprints, PIT/as-of state, OOS scopes,
  limitations, and multiple-testing context.
- Enforced timezone-aware timestamps and deterministic instrument/time ordering;
  naive timestamps are rejected before PIT or snapshot sorting.
- Added a deterministic 12-row fixture source with explicit `SAMPLE` mode and
  source/provider/retrieval/availability metadata.
- Added capability detection that does not import optional engines in core;
  Qlib/vectorbt/xtquant remain absent from `.venv` and `.venv-quant`.
- Added `QlibResearchAdapter` with a typed deterministic fallback. No Qlib
  handler, dataset, model, workflow, MLflow, or portfolio object crosses into
  Finathink contracts or JSON/UI payloads.
- Added a bounded sweep ledger that retains every experiment, failed/pending
  cell, train/validation/OOS values, robustness/instability context, and
  multiple-testing warning. It emits no “best strategy” claim.
- Added `QMTBridgeClient` as a read-only mock/bridge seam. It has bounded
  snapshot/health operations, loopback-by-default binding, token digest
  comparison, trusted-LAN token enforcement, credential/trading-field denial,
  and no order/cancel/account methods.
- Added `/research`, `/ml`, `/parameter`, `/settings/engines`, and
  `/settings/data-sources` plus read-only JSON routes under `/api/research/*`.
- Added a local, same-origin frontend bundle using Lightweight Charts 5.2.1,
  ECharts 6.1.0, and esbuild 0.28.2. The research view supports normalized
  candlesticks, volume, feature overlays, event markers, crosshair/click
  selection, inspector/tooltip synchronization, OOS sweep line, reduced
  motion, keyboard table selection, and a server-rendered no-JavaScript table
  fallback.
- Added capability, dependency-topology, visualization, research-engine,
  data-source, QMT, Qlib, vectorbt, UI, performance, security, reference, and
  external-tool review documents under `docs/p8_2/`.

## 3. Optional-engine evidence

### Qlib

The core environments remain clean. A dedicated native macOS arm64
`.venv-qlib-py312` uses Python 3.12.15 and `pyqlib==0.9.7`; `pip check`
passes. `scripts/p8_2_qlib_smoke.py` passed in that environment and in a
disposable Linux/amd64 Python 3.12 Docker check:

```json
{"lightgbm_version":"4.7.0","oos_mae":2.3976224998633064,
 "provider_initialized":false,"qlib_version":"0.9.7",
 "raw_objects_returned":false,"status":"PASS","test_rows":2,"train_rows":4}
```

This is an in-memory DatasetH-shaped fixture and a bounded Qlib `LGBModel`
train/validation/OOS smoke. It does not initialize a Qlib provider, download
market data, establish PIT correctness for a licensed source, or admit Qlib
into core. The Finathink ML Lab therefore continues to show the deterministic
fallback and the capability remains isolated/deferred.

### vectorbt

`.venv-vectorbt` contains `vectorbt==1.1.1` on Python 3.13.7, outside core and
quant environments. `pip check` and `scripts/p8_2_vectorbt_smoke.py` pass:

```json
{"license_gate":"OPTIONAL / COMMONS CLAUSE REVIEW REQUIRED",
 "max_drawdown":-0.033286364572724936,"raw_objects_returned":false,
 "rows":6,"status":"PASS","total_return":-0.033286364572724964,
 "version":"1.1.1"}
```

The smoke returns scalar summaries only. Apache-2.0 + Commons Clause and any
extra/provider terms still require legal review before distribution or hosted
admission; the Finathink-native sweep remains authoritative.

### QMT

No QMT/MiniQMT process, `xtquant` module, vendor client, credentials, or
Windows bridge is present. The mock/offline boundary is validated only. A real
QMT connection, vendor terms, transport security, certificate/token rotation,
freshness, revisions, and live data health remain unverified.

## 4. Research validity and safety boundary

Every normalized observation carries source/provider, retrieval and
availability time, adapter version, and a content fingerprint. Dataset
snapshots are bounded, ordered, duplicate-rejecting, PIT-aware, and explicit
about `SAMPLE`, `SYNTHETIC`, `CAPTURED`, `LIVE`, or `PAPER` mode. ML and sweep
specifications carry dataset/feature fingerprints and explicit train,
validation, and OOS scopes. The UI preserves limitations and never turns an
OOS comparison or a parameter cell into a recommendation.

No broker password, account credential, order/cancel path, real-money action,
or arbitrary generated-code execution path was added. The HTTP shell remains
loopback-oriented, same-origin, CSP-restricted (`script-src 'self'`), and
without remote scripts/CDN dependencies. The secret scanner skips only
known build/virtual-environment paths and has a regression test for the
isolated dependency false positive; no project credential pattern is present.

## 5. Validation gates

| Gate | Command/evidence | Result |
| --- | --- | --- |
| Core regression | `.venv/bin/pytest -q` | **PASS — 299 passed, 1 skipped** |
| Quant regression | `.venv-quant/bin/python -m pytest -q` | **PASS — 299 passed, 1 skipped** |
| P8.2 focused | `.venv/bin/pytest -q tests/p8_2 tests/validation/test_governance.py tests/validation/test_secret_scan.py tests/p7_5/test_local_app.py` | **PASS — 44 passed** |
| Python lint | `.venv/bin/ruff check src tests scripts` | **PASS** |
| Core/quant dependencies | `.venv/bin/python -m pip check`; `.venv-quant/bin/python -m pip check` | **PASS** |
| Qlib sandbox dependencies | `.venv-qlib-py312/bin/python -m pip check` | **PASS** |
| vectorbt sandbox dependencies | `.venv-vectorbt/bin/python -m pip check` | **PASS** |
| Notebook reproducibility | `jupyter nbconvert --to notebook --execute .../01_research_workflow.ipynb` | **PASS** |
| Python dependency audit | `.venv/bin/pip-audit -r requirements.lock --strict --progress-spinner off` | **PASS — no known vulnerabilities** |
| Secret scan | `.venv/bin/python scripts/secret_scan.py` | **PASS — no known credential patterns** |
| Governance | `.venv/bin/python scripts/validate_governance.py .` | **PASS after this report/state update** |
| Clean wheel install | `.venv/bin/python scripts/clean_install.py` | **PASS — built and imported `finahinking-0.1.0` wheel** |
| Frontend unit/build | `npm test`, `npm run build` in `frontend/` | **PASS — 4 tests; bundle built** |
| Frontend payload performance | `npm run perf` in `frontend/` | **PASS — 1k: 2.189 ms; 10k: 20.231 ms (Node normalizer + middle selection)** |
| Frontend dependency audit | `npm audit --omit=dev --audit-level=high` | **PASS — 0 vulnerabilities** |
| Bundle syntax/diff | `node --check site/assets/finathink-research.js`; `git diff --check` | **PASS** |
| Qlib compatibility | native and Linux/amd64 isolated smoke script | **PASS — model smoke only; provider/PIT deferred** |
| vectorbt compatibility | isolated six-row smoke script | **PASS — license gate remains open** |
| Browser DOM/E2E | no approved browser binary/headless session available; Computer Use forbidden | **NOT VERIFIED — explicit stop-condition blocker** |
| Real QMT/vendor bridge | no supported QMT host/client/credentials available | **NOT VERIFIED — explicit adapter-admission blocker** |

The frontend tests are pure Node schema/selection tests; they do not claim
browser paint, DOM event dispatch, screen-reader behavior, or mobile-device
performance. The server-rendered table and source inspection reduce the
failure surface, but browser-level evidence belongs to a later approved gate.

## 6. Remaining conditional findings

1. Browser-level DOM/E2E/CSP interaction and real accessibility testing remain
   unverified because no headless browser binary is available and Computer Use
   is forbidden by the mission/user instruction.
2. Qlib provider initialization, licensed PIT/revision fixture, and full
   normalized adapter integration remain deferred even though the isolated
   model smoke passes.
3. QMT vendor/API/terms review, supported-host transport security, and any
   live-source freshness/revision evidence remain deferred; the local state is
   `NOT CONNECTED`.
4. vectorbt Commons Clause and transitive/extra-license review remain open;
   vectorbt is not a public/core dependency.
5. Long-history browser virtualization, real chart FPS/memory, screen-reader
   timing, and QMT latency are not measured. The 10,000-point result is a
   bounded Node parser stress check, not a hardware or browser guarantee.
6. Remote/canonical GitHub reconciliation and publication are unchanged from
   P8.1; no push, merge, release, or force operation was performed.

These findings do not invalidate the local offline contracts and fallback
paths, but they prevent a full production or public-provider admission claim.

## 7. Checkpoint and human review

The authoritative state is `docs/PROJECT_STATE.md`:

- `P8.2 status: CONDITIONAL`;
- `P8.2B: WAITING FOR HUMAN REVIEW`;
- no P8.2B work has started.

The final local commit and tag are recorded in the last section below after
the working tree is committed. No remote publication is implied.
