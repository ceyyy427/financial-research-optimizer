# TradingAgents Reference Record

This is the compact external-reference record for P8.2. The detailed pattern
analysis is in [TRADINGAGENTS_REFERENCE_REVIEW.md](TRADINGAGENTS_REFERENCE_REVIEW.md).

## Identity

| Field | Value |
| --- | --- |
| Local path | `/Users/mac/Documents/Codex/2026-10-03/codex-plugin-marketplace-add-yuuhann1999-agent/TradingAgents` |
| Upstream | <https://github.com/TauricResearch/TradingAgents> |
| Classification | **D — reference laboratory** |
| Snapshot | `8b22d43d01d9ddda5d686d093d5385884622f3de` (`main`, v0.5.2) |
| License | Apache License 2.0 (`LICENSE`) |
| Package | `tradingagents` 0.5.2; CLI package `cli` |
| Audit method | local Git/source/test inspection only |
| Runtime status | not installed or imported by Finathink |

## Reference capability map

| Area | Observed implementation | Finathink use |
| --- | --- | --- |
| Workflow | LangGraph state graph; parallel analysts; explicit debate/risk routes | Learn observable stages and dependency boundaries |
| Progress | Rich live layout, statuses, message/tool stream, report preview, counters | Learn truthful progress and activity presentation |
| Reports | Shared CLI/API report writer and numbered Markdown tree | Learn durable report organization and metadata headers |
| Configuration | defaults → `.env` → typed env overrides → flags/prompts; sanitized prefs | Learn explicit precedence and safe convenience state |
| History | per-ticker SQLite checkpoint; JSON state; append-only memory log | Learn resumability and temporal history boundaries |
| Data | explicit category/tool vendor chains and typed error taxonomy | Learn adapter/fallback contracts |
| Backtest | isolated ticker/date grid, pending settlement, structured failures | Learn bounded research-job orchestration |

## Deliberate non-adoption

Finathink does not adopt TradingAgents' analyst/researcher/trader/risk/portfolio
roles, BUY/SELL/HOLD semantics, broker behavior, or automatic investment
conclusions. No repository is vendored, and no external object is allowed to
become a Finathink domain object.

## Recheck triggers

Re-audit this record before any future adapter work if the upstream release,
license, checkpoint format, vendor contract, or CLI report schema changes.
