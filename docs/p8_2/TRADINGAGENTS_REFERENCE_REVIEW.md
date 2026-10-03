# TradingAgents Reference Review (P8.2 Stage A)

Status: read-only reference audit; no TradingAgents code was copied, vendored,
imported, or installed into Finathink.

Audit date: 2026-10-03 (Asia/Shanghai)

## Scope and snapshot

The inspected checkout is:

`/Users/mac/Documents/Codex/2026-10-03/codex-plugin-marketplace-add-yuuhann1999-agent/TradingAgents`

The checkout was clean on `main`, tracking `origin/main` at
`https://github.com/TauricResearch/TradingAgents.git`.

| Fact | Observed value |
| --- | --- |
| HEAD | `8b22d43d01d9ddda5d686d093d5385884622f3de` |
| package version | `0.5.2` (`tradingagents/__init__.py`) |
| latest tag | `v0.5.2` |
| tracked files | 204 |
| Python files | 177 |
| top-level test files | 84 |
| declared license | Apache License 2.0 (`LICENSE`) |
| Python requirement | `>=3.11` |

This is a reference laboratory (classification **D**), not a Finathink runtime
dependency. The repository's trading language and decision roles are outside the
scope of what Finathink should adopt.

## Required study labels

**WHAT WORKS WELL:** explicit phase progress, bounded work, report parity,
configuration precedence, resumable history, and typed data failures.

**WHY IT WORKS:** the display and persistence layers consume structured state
and explicit contracts instead of guessing from model prose.

**WHAT FINATHINK SHOULD LEARN:** stage ownership, truthful status, durable
artifact/report organization, provenance-safe configuration, and recoverable
error semantics.

**WHAT FINATHINK SHOULD NOT COPY:** trading decisions, broker behavior, agent
roles, or the external repository's domain vocabulary.

## What works well and why

### Progress and workflow visibility

`cli/display.py` builds a Rich `Layout` with a fixed header, a progress/messages
area, a current-report panel, and a statistics footer. The progress table groups
agents by Analyst, Research, Trading, Risk, and Portfolio teams and uses explicit
`pending`, `in_progress`, `completed`, and `error` states. Tool calls and model
messages are separate rows, while token/tool/LLM counts and elapsed time remain
visible. A spinner is used only for work in progress.

This works because the display is derived from a small `MessageBuffer` state
rather than trying to infer progress from free-form prose. `get_completed_reports_count`
also requires both report content and the finalizing agent's completed state, so
an interim update is not presented as a finished report.

Finathink should learn the state vocabulary, phase ownership, and truthful
progress semantics. Finathink should use its own web shell and research status
contract, not copy the Rich terminal layout.

### Pipeline and phase boundaries

`tradingagents/graph/setup.py` constructs a LangGraph state graph. Selected
analysts run as parallel top-level branches; the research debate starts after all
selected analysts file reports, then proceeds to Research Manager, Trader, three
risk debators, and Portfolio Manager. Each analyst has a private subgraph for
model/tool turns. A `max_tool_rounds` cap routes a looping analyst to a wrap-up
turn rather than allowing recursion to run indefinitely.

The graph uses explicit conditional path maps (`DEBATE_PATH_MAP` and
`RISK_ANALYSIS_PATH_MAP`). This makes a routing change fail visibly at the graph
boundary instead of silently jumping to an unintended node. `stream_run` exposes
messages and task/state chunks so a caller can render reports as they land.

Finathink should learn to model research as observable stages with an explicit
transition contract, including an honest terminal state and a bounded work unit.
It should not import TradingAgents' debate, trader, or portfolio-manager
semantics.

### Report organization

`tradingagents/reporting.py` is shared by the CLI and the programmatic graph API.
It writes a numbered report tree (`1_analysts`, `2_research`, `3_trading`,
`4_risk`, `5_portfolio`) plus `complete_report.md`. The header records analysis
date, generation time, package version, provider/models, selected analysts,
debate depth, and vendor configuration. Tests in `tests/test_reporting.py` pin
CLI/API parity and ensure endpoints, secrets, and local paths are not recorded.

The useful pattern is a durable, inspectable report tree with a consolidated
reading path. Finathink should use its own `ResearchRun`/`QuantRun` artifacts,
fingerprints, evidence links, and research-only language; it must not reproduce
the numbered trading-decision report as a product contract.

### Configuration and provider abstraction

Configuration is layered: defaults in `tradingagents/default_config.py`,
`.env` loading in `tradingagents/__init__.py`, `TRADINGAGENTS_*` environment
overrides, CLI flags, and interactive selections. `cli/prefs.py` persists only
stable choices (provider, models, language, analyst set, depth, endpoint),
sanitizes remembered values against current choices, and writes atomically.

Data access is routed through `tradingagents/dataflows/router.py`. Category and
tool-level vendor chains are explicit; the router does not silently add vendors
the user did not configure. A run's `run_settings()` uses an allowlist so keys,
endpoints, and filesystem paths are not written into reports.

Finathink should learn explicit precedence, sanitized convenience state,
configuration fingerprints, and allowlisted provenance. Its adapter layer must
remain the authority for Finathink contracts.

### History, checkpoints, and reproducibility cues

`tradingagents/graph/checkpointer.py` stores per-ticker SQLite checkpoints. The
thread ID includes ticker, date, selected analysts, debate/risk depth, asset mode,
portfolio fingerprint, and a settings digest; incompatible runs therefore do
not resume stale graph state. Successful runs clear their checkpoint.

`tradingagents/memory/log.py` stores pending decisions and later resolved outcomes
in an append-only Markdown log. Settlement records the outcome window and a
resolution date, and historical runs only read lessons known by their as-of
date. Final graph state is also written as per-ticker JSON, and a backtest has its
own result directory and memory log.

These are useful patterns for continuity and temporal honesty. Finathink should
retain its own immutable `ResearchRun` and `QuantRun` fingerprints rather than
adopting a trading decision log.

### Error and fallback behavior

`tradingagents/dataflows/errors.py` defines a small behavior-oriented hierarchy:
`NoMarketDataError`, `VendorUnavailableError`, and `VendorNotConfiguredError`.
The router distinguishes “the symbol has no usable data” from “the vendor could
not answer.” It emits explicit `NO_DATA_AVAILABLE` or `DATA_UNAVAILABLE` sentinels
and tells the agent not to estimate or fabricate values. Optional enrichment
categories degrade to a sentinel; core price/fundamental/news failures stay
visible.

The CLI also checks for unattended gaps before making a model call and names the
missing flags/environment variables. Backtests isolate cell failures, keep a
failure list, and continue the sweep; pending cells remain pending until their
window can be settled.

Finathink should learn the distinction between unavailable, no-data, pending,
and failed, and should carry the distinction into UI and provenance. It should
not copy provider-specific wording or turn a sentinel into an investment claim.

## UI patterns (UI PATTERNS) Finathink can learn

| Pattern | Reference evidence | Finathink adaptation |
| --- | --- | --- |
| Phase-based status wall | `cli/display.py`, `MessageBuffer.agent_status` | Stage rail for Events, Knowledge, Quant, Strategy, and Paper research |
| Current report preview | `MessageBuffer._update_current_report` | Show the latest evidence-backed artifact, with source and timestamp |
| Separate activity stream | `Messages & Tools` panel | Activity panel with redacted tool/provider details |
| Explicit state colors | `pending`/`in_progress`/`completed`/`error` | Finathink status tokens; never color-only, always text + accessible label |
| Bounded progress | `max_tool_rounds`, elapsed/token stats | Bounded local jobs, progress estimates only when measurable |
| Completion semantics | content + finalizer status | Artifact readiness only after validation and provenance checks |

## Pipeline patterns (PIPELINE PATTERNS)

1. Normalize the user's selection into an execution plan.
2. Run independent research units concurrently where safe.
3. Expose each unit's status and completed artifact separately.
4. Start dependent synthesis only after its declared inputs are present.
5. Bound external/tool loops and surface a recoverable failure.
6. Store a machine-readable final state and a human-readable report.

Finathink's pipeline must additionally preserve point-in-time data, evidence
references, research validity, and paper-only boundaries.

## Report patterns (REPORT PATTERNS)

- Shared writer for interactive and programmatic paths.
- Stable section names and a consolidated report.
- Header metadata describing what produced the result.
- Separate raw activity/log data from the polished report.
- No secret, endpoint credential, or machine-local path in persisted output.

## Configuration patterns (CONFIGURATION PATTERNS)

- Environment variables are explicit and type-coerced; invalid values fail at
  startup rather than silently falling back.
- CLI flags override only the field they answer; omitted flags preserve explicit
  environment choices.
- Remembered preferences are convenience state, validated against current
  options, and written atomically.
- Provider/vendor selection is an explicit ordered chain.

## History patterns (HISTORY PATTERNS)

- Checkpoint identity includes all graph-shape and research-input choices.
- A completed checkpoint is deleted, preventing accidental stale resume.
- Backtests isolate their log and results from the live memory log.
- Resolution dates prevent future outcomes from entering a historical run.

## Error / progress patterns (ERROR / PROGRESS PATTERNS)

- Separate unavailable provider, no data, invalid input, and pending outcome.
- Preserve the original failure in logs while returning an actionable safe
  sentinel to the research layer.
- Continue independent backtest cells while retaining a structured failure list.
- Before an unattended run, report every missing input at once.

## What Finathink must not copy

- BUY/SELL/HOLD decision UX or an automatic investment recommendation.
- Trader, portfolio-manager, broker, or order-routing behavior.
- TradingAgents' agent names and debate narrative as Finathink's domain model.
- A terminal-first UI as a substitute for chart, provenance, and education views.
- External graph/report objects leaking into `ResearchRun`, `QuantRun`, or
  `StrategySpec`.

## Evidence and limitations

Evidence was collected with `git`, `rg`, `sed`, and local source/test inspection;
no GUI/computer-use operation, networked model call, or TradingAgents execution
was performed. This review establishes reference patterns only. It does not
claim that Finathink has integrated TradingAgents, or that the reference's
providers are available in this environment.

### Evidence map

| Concern | Primary files inspected |
| --- | --- |
| Live UI/status wall | `cli/display.py`, `cli/run.py`, `cli/stats_handler.py` |
| Selection/config precedence | `cli/main.py`, `cli/selections.py`, `cli/prompts.py`, `cli/prefs.py`, `tradingagents/default_config.py` |
| Graph/workflow | `tradingagents/graph/setup.py`, `graph/analyst_execution.py`, `graph/propagation.py`, `graph/conditional_logic.py` |
| Run lifecycle/checkpoints | `tradingagents/graph/trading_graph.py`, `graph/checkpointer.py` |
| Report/history | `tradingagents/reporting.py`, `tradingagents/memory/log.py`, `memory/settlement.py`, `tradingagents/backtest.py` |
| Vendor/error boundary | `tradingagents/dataflows/router.py`, `dataflows/errors.py`, `dataflows/net.py`, `dataflows/date_window.py` |
| Regression evidence | `tests/test_graph_end_to_end.py`, `tests/test_reporting.py`, `tests/test_checkpoint_resume.py`, `tests/test_vendor_errors.py`, `tests/test_cli_headless.py`, `tests/test_suite_isolation.py` |
