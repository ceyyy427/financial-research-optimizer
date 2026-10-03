# Finathink P8.2 Dependency Topology

**Date:** 2026-10-03 (Asia/Shanghai)
**Purpose:** keep core runtime, frontend build, optional research sandboxes,
and a possible QMT bridge separate enough that one provider cannot redefine
Finathink or destabilize a clean install.

## Topology

```text
                         ┌─────────────────────────────┐
                         │ Finathink core (`.venv`)    │
                         │ Python >=3.11               │
                         │ contracts / provenance / UI │
                         └──────────────┬──────────────┘
                                        │ typed JSON-safe adapters
             ┌──────────────────────────┼──────────────────────────┐
             │                          │                          │
   `.venv-quant`                 `frontend/`                  local fixtures
   existing quant runtime        npm + esbuild                 BLS/market samples
   no optional engine            Lightweight Charts             captured/sample labels
                                 ECharts
             │                          │
             │                          └── same-origin static bundle
             │
   ┌─────────┴──────────┐       ┌──────────────────────┐
   │ `.venv-qlib-py312` │       │ `.venv-vectorbt`     │
   │ optional, planned  │       │ optional, planned    │
   │ Qlib/LightGBM      │       │ vectorbt + extras    │
   └─────────┬──────────┘       └──────────┬───────────┘
             │ Qlib adapter                 │ sweep adapter
             └──────────────┬───────────────┘
                            ▼
                   Finathink ML/Sweep result

   possible external Windows host
   QMT/MiniQMT + official login
              │ loopback/trusted bridge, read-only
              ▼
       Finathink QMT data adapter
```

The arrows represent a one-way normalization boundary. Optional environments
may produce files/JSON artifacts, but raw provider classes, handlers, portfolio
objects, credentials, and execution methods never enter `src/finahinking`.

## Environment manifest

| Environment | Current location/status | Required contents | Must not contain | Fallback |
| --- | --- | --- | --- | --- |
| Core | `.venv`; Python 3.13.7 observed | Finathink package, NumPy 2.5.3, pandas 3.0.6, test/release tooling | Qlib/vectorbt/QMT client; broker secrets | Existing Finathink engines and fixtures |
| Quant | `.venv-quant`; Python 3.13.7 observed | Existing quant/research dependencies and tests | Optional provider packages unless explicitly isolated | Core quant engine |
| Frontend build | `frontend/`; Node v24.21.0, npm 11.19.0 | `lightweight-charts@5.2.1`, `echarts@6.1.0`, `esbuild@0.28.2` | Python runtime state, remote runtime scripts | Server HTML and accessible table |
| Qlib | `.venv-qlib-py312` exists; isolated smoke PASS | Pinned `pyqlib==0.9.7`, approved in-memory fixture, LightGBM baseline | Core package imports, unreviewed data downloads, provider state | Finathink ML adapter fallback |
| vectorbt | `.venv-vectorbt` exists; core/quant remain absent | Pinned vectorbt release, approved fixture, license notices | Core package imports, `full` extras by default | Finathink-native parameter sweep |
| QMT bridge | Possible `.venv-qmt` on a supported bridge host; **not created** | Minimal read-only bridge and health checks | Broker password, order/cancel/account methods | Offline/mock QMT provider and fixture source |

The two core Python environments are both Python 3.13.7. Qlib's audited
upstream classifiers currently stop at 3.12, so a Python 3.12 runtime is a
conservative prerequisite rather than an assumed capability. At initial
inventory time no Qlib, vectorbt, or `xtquant` import was available in core;
the later isolated vectorbt smoke is intentionally outside that invariant.

The read-only probe checks the planned `.venv-qlib-py312` name. The optional
vectorbt smoke uses `.venv-vectorbt`; neither environment is part of a clean
core install or the published wheel.

## Version and license ledger

| Dependency/provider | Version observed or pinned | License/terms | Required? | Admission note |
| --- | --- | --- | --- | --- |
| NumPy | 2.5.3 in project environments | BSD-style upstream terms (existing lock governs) | Core | Existing dependency; do not widen for optional tools |
| pandas | 3.0.6 in project environments | BSD-style upstream terms (existing lock governs) | Core | Existing dependency |
| Lightweight Charts | 5.2.1 | Apache-2.0 | First UI slice | Frontend-only pinned package |
| ECharts | 6.1.0 | Apache-2.0 | First UI slice | Frontend-only pinned package |
| esbuild | 0.28.2 | MIT | Build only | Frontend-only pinned package |
| Qlib / `pyqlib` | 0.9.7 published; commit separately recorded | MIT | Optional | Dedicated Python 3.12 spike and fixture required |
| vectorbt | 1.1.1 installed in isolated sandbox; core absent | Apache-2.0 + Commons Clause; extras vary | Optional | Smoke passed; legal/distribution review required |
| TradingAgents | v0.5.2 reference snapshot | Apache-2.0 | No | Separate read-only reference checkout |
| QMT / MiniQMT / `xtquant` | Not verified | Vendor/proprietary terms not verified | Optional adapter | No install/connection claim |

License records are evidence for admission, not legal advice. A future public
or hosted distribution needs a fresh notice and legal review, especially for
vectorbt's Commons Clause and QMT vendor terms.

## Dependency edges and ownership

1. `local_app.py` and P8.2 contracts depend only on core Python and existing
   Finathink modules.
2. `research_view` consumes a Finathink-owned normalized payload; it does not
   import Qlib, vectorbt, or QMT.
3. The frontend bundle depends on pinned chart libraries at build time. It is
   served as a same-origin static asset and has no CDN fallback.
4. `QlibResearchAdapter` accepts a Finathink dataset/ML specification and
   returns a Finathink ML result. Qlib handlers/models/results are private to
   the adapter process.
5. The sweep adapter accepts a Finathink specification and returns every
   experiment and its validity metadata. A vectorbt portfolio is an internal
   implementation detail.
6. The QMT bridge returns canonical observations and data-health metadata only.
   Authentication and vendor session ownership remain outside the core app.

## Installation and upgrade controls

- Install optional packages only after metadata, license, Python compatibility,
  and fixture provenance are recorded.
- Never add Qlib/vectorbt/QMT to `pyproject.toml` core dependencies merely to
  make a demo pass.
- Capture exact package versions, Python version, platform, `pip freeze`,
  `pip check`, license notices, and a smoke-test artifact for every optional
  environment.
- Keep the frontend lockfile independent of `requirements.lock`; run the
  frontend audit/build in its own gate.
- Upgrade one environment at a time and rerun core absence tests afterward.
- If a provider cannot be installed or its terms are unclear, leave the
  capability as `NOT INSTALLED`/`DEFERRED` and retain the in-house fallback.

## Network and secret boundary

Core P8.2 can run offline from package fixtures. External network access is an
explicit adapter concern and must record source URL, retrieval time, timezone,
as-of policy, and response fingerprint. QMT login remains in the vendor client;
Finathink logs only non-secret connection state and normalized market data.
Remote JavaScript, remote fonts, arbitrary callback URLs, and user-supplied
code execution are not dependencies of the local UI.

## Clean-install invariant

A clean install that excludes `.venv-qlib-py312`, `.venv-vectorbt`, and any QMT
client must still be able to:

- import the Finathink package;
- render existing routes and the research fallback;
- load the local chart bundle or its table fallback;
- run the full core test suite;
- report optional capabilities accurately.

The final validation report must attach command output for this invariant and
identify any unsupported platform-specific check instead of silently skipping
it.
