# Finathink P8.2 Capability Matrix

**Audit date:** 2026-10-03 (Asia/Shanghai)
**Mission rule:** capability availability is evidence-based; a package name in
this table is not an admission decision.
**Computer Use:** forbidden; all inventory and checks used shell, source
inspection, package metadata, and headless tooling.

## Inventory method

The configured skill roots were searched for `SKILL.md` files:

```text
find /Users/mac/.codex/skills /Users/mac/.agents/skills \
  /Users/mac/.codex/plugins/cache/openai-bundled \
  /Users/mac/.codex/plugins/cache/openai-curated-remote \
  -name SKILL.md -type f
```

Observed count: **161**. The inventory includes local, bundled, and curated
plugin skills; it does not imply that all 161 are relevant to P8.2 or that any
new skill was installed. The selected skills below were read/used because they
map to a concrete P8.2 workstream.

## Selected skill/tool usage

| Skill or capability | Purpose in P8.2 | Available/trusted | Install needed | Installed for P8.2 | Permissions | Used in |
| --- | --- | --- | --- | --- | --- |
| `superpowers:using-superpowers` | Establish skill routing and work discipline | Yes, first-party bundled | No | No new install | Local planning only | Session setup and skill routing |
| `superpowers:brainstorming` | Explore product/interaction choices before implementation | Yes, first-party bundled | No | No new install | No code or external mutation by itself | P8.2 interaction/design brief |
| `superpowers:writing-plans` | Turn the mission into ordered tasks and gates | Yes, first-party bundled | No | No new install | Plan/document output | P8.2 execution plan |
| `superpowers:test-driven-development` | Contract and UI behavior tests before implementation | Yes, first-party bundled | No | No new install | Tests and local files only | Contract, adapter, chart tests |
| `superpowers:systematic-debugging` | Root-cause workflow for failing gates | Yes, first-party bundled | No | No new install | Diagnostics; no destructive reset | Gate failures and recovery |
| `superpowers:verification-before-completion` | Require evidence before final claims | Yes, first-party bundled | No | No new install | Final audit/report discipline | P8.2 final validation |
| `frontend-design` | Distinct, intentional research workspace visual system | Yes, local trusted skill | No | No new install | Same-origin local UI assets | Research workspace UI |
| `design-system` | Primitive → semantic → component tokens | Yes, local trusted skill | No | No new install | Documentation/CSS guidance | UI token and component review |
| `ui-ux-pro-max` | Accessibility, focus, responsive and chart interaction review | Yes, local trusted skill | No | No new install | UI review; no browser GUI automation | Chart/table/settings review |
| `visualize:visualize` / data visualization guidance | Match chart family to question; preserve context and uncertainty | Yes, bundled/curated | No | No new install | Chart design and headless checks | Chart and sweep-panel design |
| `software-engineering` | Durable contracts, dependencies, maintainability | Yes, local trusted skill | No | No new install | Architecture and review | Adapter/dependency topology |
| `financial-research-optimizer` | PIT/OOS/provenance and source-quality constraints | Yes, local trusted skill | No | No new install | Financial research semantics; no investment advice | Data and research validity gates |
| `gsap-*` family | Motion guidance if needed | Yes | No | No | Optional; no remote runtime dependency | Deferred motion polish only |
| Node/npm + esbuild | Bundle local chart controller | Available (`node v24.21.0`, `npm 11.19.0`) | No | Frontend workspace only | Build-time only; no Python runtime coupling | `frontend/build.mjs` and asset gate |
| Lightweight Charts | Candles, crosshair, range and markers | Metadata inspected (`5.2.1`, Apache-2.0) | Frontend workspace only | Pinned; Node tests/build pass; browser render unverified | Browser renders normalized values only | `frontend/src/research.js` |
| ECharts | Sweep/quant research panels | Metadata inspected (`6.1.0`, Apache-2.0) | Frontend workspace only | Pinned; Node tests/build pass; browser render unverified | Browser renders server values only | `frontend/src/research.js` |

No random AI agent, unreviewed plugin, or external repository was installed.
The P8.2 frontend lock is separate from Python environments and must not alter
the core Python dependency lock.

## Capability/provider admission matrix

| Capability/provider | Class | Exact observed metadata | Environment | Status at inventory | Finathink boundary | Fallback / decision |
| --- | --- | --- | --- | --- | --- | --- |
| Finathink core/runtime | A — core | Python project `>=3.11`; NumPy/pandas core; existing P4–P7.5 contracts | `.venv` and `.venv-quant` (both Python 3.13.7) | Available | Owns `ResearchRun`, `QuantRun`, provenance, PIT/OOS, UI vocabulary | Authoritative; keep independent of optional engines |
| Lightweight Charts | A — core UI dependency for first slice | `5.2.1`, Apache-2.0 | `frontend/` build workspace | Pinned; Node tests/build pass; browser render unverified | Receives normalized chart payload only | Table/empty-state fallback if bundle unavailable |
| ECharts | A — core UI dependency for research panels | `6.1.0`, Apache-2.0 | `frontend/` build workspace | Pinned; Node tests/build pass; browser render unverified | Receives normalized values only | Text/table panel if unavailable |
| esbuild | A — build tool | `0.28.2`, MIT | `frontend/` only | Pinned build tool | Produces same-origin static asset | Keep source/headless tests if build unavailable |
| TradingAgents | D — reference laboratory | v0.5.2, commit `8b22d43`; Apache-2.0 | Separate local checkout; not imported | Audited read-only | Study progress/report/error patterns only | No runtime dependency; no trading semantics copied |
| Qlib / `pyqlib` | C — optional research sandbox | PyPI `0.9.7`; upstream MIT; Python classifiers through 3.12 | Native macOS arm64 `.venv-qlib-py312` (Python 3.12.15), plus disposable Linux/amd64 check | Isolated import/LightGBM OOS smoke PASS; provider/PIT path unverified | Typed adapter to Finathink ML result; no raw Qlib objects | Internal ML baseline; defer admission until provider fixture and human gate |
| vectorbt | C — optional research sandbox | `1.1.1`; Apache-2.0 + Commons Clause | Isolated `.venv-vectorbt` (Python 3.13.7) | Installed in sandbox; smoke PASS; absent from core/quant | Typed sweep adapter; no raw `Portfolio` | In-house sweep remains core fallback; legal review before distribution |
| QMT / MiniQMT / `xtquant` | B — production adapter candidate | Vendor terms/version not verified | Possible external Windows host/bridge; no local client | Not connected | Read-only OHLCV/events normalized to Finathink records | Fixture/mock source; investigate only with separate approval |
| BLS fixture/captured source | A/B existing admitted source | Existing local fixture and P6.5 provenance model | Core runtime/package fixture | Available as sample/captured evidence | Existing data/provenance contracts | Keep source mode explicit |
| AkShare | E/C pending review | Terms/license/API behavior not verified here | None | Deferred | Future adapter only | No UI capability claim |
| Tushare | E/C pending review | Terms/license/API plan not verified here | None | Deferred | Future adapter only | No UI capability claim |
| React Flow | C optional graph renderer | Metadata inspected only; not required for first slice | None | Deferred | Future feature graph adapter | Text/graph summary fallback |
| TanStack Table | C optional table enhancement | Metadata inspected only; not required for first slice | None | Deferred | Future table adapter | Native accessible table |

## State vocabulary exposed to users

Capability detection must return one of `AVAILABLE`, `NOT INSTALLED`,
`NOT CONNECTED`, `LOGIN REQUIRED`, `STALE`, `ERROR`, or `DEFERRED`. A UI card
must include the state text and a recovery/next-action explanation; color alone
is not a capability signal.

## Permission and security review

- Core and frontend work use local files, local test processes, and bounded
  package metadata. No credentials are required for the offline P8.2 slice.
- QMT authentication remains inside the official QMT client. Finathink may
  receive a short-lived, explicitly configured bridge token but never a broker
  password.
- Optional engines run in separate environments and receive only normalized,
  approved fixture/dataset inputs.
- Generated/model code is displayed as an artifact and is never executed from
  user text.
- No external dependency may add order, account, cancel, or live-execution
  methods to the Finathink domain surface.

## Installation policy

No new Codex skill installation is required for the documented P8.2 work.
Frontend packages are pinned in the isolated `frontend` workspace. Qlib,
vectorbt, QMT, and deferred providers are not installed into `.venv` or
`.venv-quant`; any future spike needs its own environment, exact version,
license record, smoke evidence, and human admission gate.

## Evidence limitations

This matrix records inventory-time facts. Package “available” means metadata
or a local command was observed, not that a full integration passed. The final
validation report must update statuses after tests and must preserve
`NOT VERIFIED` where no compatible environment or source connection exists.
