# External Quantitative Tool Matrix (P8.2 Stage A)

This matrix records admission posture and the latest local smoke evidence; a
sandbox smoke is not production admission and no external engine is allowed to
become a Finathink domain object. Audit date: 2026-10-03.

| Tool | Role | Class | License | Environment / install status | Adapter boundary | UI / research capability | Security / fallback | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Finathink core | Authoritative contracts, provenance, local research runtime | A — core | Finathink MIT (repository `LICENSE`) | Current project; Python 3.11+; core tests already own the runtime | N/A; `ResearchRun`, `QuantRun`, `FeatureDefinition`, `StrategySpec` remain authoritative | Web shell, evidence, quant, strategy and paper workflows | Local-first; no broker/order routing; in-house engine is fallback | Keep authoritative |
| TradingAgents | Workflow/progress/report reference laboratory | D — reference | Apache 2.0 (`TradingAgents/LICENSE`) | Local checkout at `/Users/mac/Documents/Codex/2026-10-03/codex-plugin-marketplace-add-yuuhann1999-agent/TradingAgents`; not installed | Read-only study; no runtime adapter | Rich progress wall, tool/activity stream, report tree, checkpoints | Do not copy trading decisions or provider secrets; Finathink UI/contracts remain fallback | Reference only; see `TRADINGAGENTS_REFERENCE_REVIEW.md` |
| Qlib (`pyqlib`) | ML/data-handler/training workflow candidate | C — optional sandbox | MIT (upstream `LICENSE`, `pyproject.toml`) | Native macOS arm64 Python 3.12.15 `.venv-qlib-py312` install, `pip check`, and in-memory import/LightGBM OOS smoke PASS; provider/PIT smoke not run | Proposed `QlibResearchAdapter` → normalized ML result; no raw Qlib objects | Feature handlers, LightGBM baseline, training/validation/OOS and experiment workflow | Large dependency/native surface; data download and point-in-time policy must be controlled; core works without it | Defer admission until provider/PIT fixture, native/approved deployment, license/security review |
| vectorbt | Fast parameter/sensitivity sweep candidate | C — optional sandbox | Apache 2.0 + Commons Clause; optional extras may differ | Isolated `.venv-vectorbt` on Python 3.13.7; vectorbt 1.1.1 smoke PASS; absent from core/quant | Proposed sweep adapter → `ParameterSweepSpecification`/`SweepResult`; no raw `Portfolio` | Heatmaps, sensitivity curves, parameter grids and robustness maps | License may constrain hosted/commercial use; optional extras/API/native risks; in-house engine is fallback | Defer admission until legal review + adapter normalization |
| QMT / MiniQMT / `xtquant` | Read-only A-share market-data bridge candidate | B — production adapter candidate | Proprietary/vendor terms **not verified** | No QMT/MiniQMT process or `xtquant` module found locally; no client/install attempted | Future QMT bridge → canonical OHLCV/events/metadata with source and retrieval time | Data-source settings, connection state, data-health panel | Keep login in official client; no broker password or order API; absence must degrade safely | Do not claim connected; investigate separately |
| AkShare | Public-market data candidate | C/E pending review | License/terms **not verified in this audit** | Not installed or tested | Future data-provider adapter only | Potential event/price tables | Source terms, rate limits, reproducibility and PII/security need review | Deferred pending source audit |
| Tushare | A-share data candidate | C/E pending review | License/terms/API plan **not verified in this audit** | Not installed or tested | Future data-provider adapter only | Potential fundamental/market data | Key handling, quotas, redistribution and point-in-time behavior need review | Deferred pending source audit |
| Lean | Backtest/reference candidate | D/E pending review | License/compatibility **not verified in this audit** | Not installed or tested | Would require a normalization adapter | Potential event-driven simulation | Domain and licensing fit unreviewed | No admission decision |
| `bt` | Backtest/reference candidate | D/E pending review | License/compatibility **not verified in this audit** | Not installed or tested | Would require a normalization adapter | Potential portfolio/strategy analysis | Domain and licensing fit unreviewed | No admission decision |
| Alphalens Reloaded | Factor tear-sheet/reference candidate | D/E pending review | License/compatibility **not verified in this audit** | Not installed or tested | Would require a factor-result adapter | Factor diagnostics and tear sheets | Must preserve Finathink provenance and OOS policy | No admission decision |
| PyPortfolioOpt / Riskfolio-Lib | Portfolio analytics candidates | C/E pending review | License/compatibility **not verified in this audit** | Not installed or tested | Would require typed optimizer/result adapters | Allocation/risk views only; no execution | Optimizer assumptions and license need review; paper-only fallback | No admission decision |
| QuantStats | Performance-reporting candidate | C/E pending review | License/compatibility **not verified in this audit** | Not installed or tested | Would require report/artifact adapter | Performance/risk reports | Report must not imply live advice; license and dependency audit required | No admission decision |

## Matrix rules

1. A downloaded repository is not automatically a runtime dependency.
2. Every admitted tool gets a pinned version, isolated environment where needed,
   license record, security review, adapter contract, and offline fallback.
3. External objects do not cross into Finathink domain models.
4. UI copy must say whether data/results are sample, local, connected, pending,
   or unavailable; no capability is implied by a row marked “candidate.”
5. QMT remains data-first and read-only; no order-routing methods are exposed.

## Evidence links

- [TradingAgents reference record](TRADINGAGENTS_REFERENCE.md)
- [Qlib reference](QLIB_REFERENCE.md)
- [VectorBT reference](VECTORBT_REFERENCE.md)
- [Qlib upstream](https://github.com/microsoft/qlib)
- [VectorBT upstream](https://github.com/polakowo/vectorbt)
