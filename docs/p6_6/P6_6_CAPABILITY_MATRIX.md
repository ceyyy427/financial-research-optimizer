# P6.6 Capability Matrix

**Snapshot:** 2026-10-03. “Installed” describes the current workspace; it does
not authorize adding a dependency. A capability gap must be demonstrated before
installation.

| Capability | Purpose | Required stage | Existing | Trusted | Needs installation | Installed | Security boundary | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Planning and review | Phase order and gates | all | YES | YES | NO | YES | Plan is advisory; tests remain authoritative | use existing planning/review skills |
| Feature calculations | returns, rolling statistics, ranks | feature layer | YES | YES | NO | YES | pandas/NumPy deterministic transforms only | reuse `features.core` and add bounded registry |
| P5 backtest | historical execution and costs | backtest | YES | YES | NO | YES | `BacktestEngine` is the execution authority | reuse |
| P5.5 validity/OOS | splits, freeze, multiple testing | validation | YES | YES | NO | YES | explicit periods and frozen fingerprints | reuse |
| P6 typed gateway | quant provenance | orchestration | YES | YES | NO | YES | typed request and gateway allowlist | reuse |
| P6 learning | cards and encounters | learning | YES | YES | NO | YES | evidence and limitations carried into cards | reuse |
| P6.5 evidence/repository | source and artifact lineage | export/persistence | YES | YES | NO | YES | approved source boundary and fixed SQL | reuse |
| Static code scan | educational export safety | code export | YES (bounded local AST scanner) | YES (focused tests) | NO | YES | P6.6 AST allowlist; no generated code execution | use local implementation; do not install a package |
| PostgreSQL driver | production repository | persistence | NO | NO | NO | NO | not required by deterministic slice | defer |
| TA-Lib/vectorbt/Backtrader/Qlib | indicator or execution convenience | feature/backtest | NO | NO | NO | NO | adds native/dependency trust surface | deny absent a documented gap |
| Feature-engine/AutoML/ML framework | generic feature discovery | feature layer | NO | NO | NO | NO | outside human-understandable scope | defer |
| Broker SDK/MCP/plugin | live execution | forbidden | NO | NO | NO | NO | direct contradiction of product boundary | explicitly prohibited |
| New market-data adapter | paper data | source access | NO | NO | NO | NO | P6.5 Source Admission remains mandatory | defer |
| New package or plugin | general capability | all | NO | NO | NO | NO | no capability gap demonstrated | no installation |

## Decision

The existing Python, pandas/NumPy, P4–P6.5 contracts, and repository-native
tools cover the P6.6 slice. No plugin, MCP connector, broker integration,
provider SDK, quant library, ML framework, database driver, or secret is
installed. This preserves the P6.5 trust and network boundaries.
