# P6.5 Capability Matrix

**Snapshot:** 2026-10-03. “Installed” means available in this workspace or
runtime; it does not mean that a new package was added during P6.5. The matrix
is an audit record, not an instruction to install everything listed.

| Capability | Required task | Existing skill / tool | Available | Trusted | Needs installation | Installed | Why used | Where used | Security boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Planning and decomposition | Freeze scope and order work | `superpowers:writing-plans`, local design/plan docs | YES | YES | NO | YES | Defines dependencies and gates before code | `docs/superpowers/plans/2026-10-03-finahinking-p65-plan.md`, this folder | Plan is advisory; implementation still requires tests and gate evidence |
| Architecture reasoning | Inspect existing P4–P6 contracts | `superpowers:brainstorming`, `software-engineering` | YES | YES | NO | YES | Prevents duplicate quant/provenance abstractions | architecture/design review | No code execution or source authority |
| Parallel review | Independent audits | `superpowers:dispatching-parallel-agents`, Codex collaboration | YES | YES | NO | YES | Separates source, architecture, security, and product checks | audit threads and gate review | Agents share contracts; no independent schema forks |
| Test-first implementation | Contract and regression tests | `superpowers:test-driven-development`, `pytest` | YES | YES | NO | YES | Makes capture, temporal, SQL, claim, and product boundaries executable | `tests/p6_5`, existing `tests/` | Fixtures are bounded and deterministic; no live network in default suite |
| Debugging and verification | Diagnose failures and prove completion | `superpowers:systematic-debugging`, `verification-before-completion` | YES | YES | NO | YES | Requires evidence rather than a green-looking narrative | focused/full test gates | No destructive reset or unreviewed workaround |
| Quant research validity | Review P6 quant reuse and financial limitations | `financial-research-optimizer`, existing P6 planner/gateway | YES | YES | NO | YES | Keeps quantitative claims bounded and source-aware | `p6_5.product`, P6 gateway | No trading, brokerage, alpha promise, or unrestricted provider |
| Data quality | Check grain, missingness, numeric and temporal validity | `data-analytics:analyze-data-quality` | YES | YES | NO | YES | Provides a transparent quality report | `p6_5.evaluation`, P6.5 tests | Report diagnoses rows; it never silently repairs source facts |
| Evaluation/validation | Validate methods, provenance, limitations | `data-analytics:validate-data` | YES | YES | NO | YES | Independent quality and gate review | evaluation docs and final gate | No causal effect claim from the pre/post proxy |
| Local file editing | Add code/docs with reviewable diffs | `apply_patch`, `rg`, `git diff` | YES | YES | NO | YES | Required workspace-native editing and inspection | all P6.5 files | Paths are explicit; no broad destructive operations |
| Python runtime | Canonical records, adapter, repository adapter | Existing `.venv` Python 3.11+ | YES | YES | NO | YES | Uses standard library plus existing project stack | `src/finahinking/p6_5` | No dynamic `eval`/`exec`/compile; bounded JSON |
| Ruff | Static style and lint gate | Existing `ruff` executable | YES | YES | NO | YES | Catches unsafe/unfinished code paths | final validation | Lint is read-only |
| BLS official source | First authoritative CPI capture | `BLSClient`; official `api.bls.gov` endpoint and release pages | YES | YES | NO | YES (client/fixture) | Original publisher, release timing, and API response | `p6_5.bls`, `fixtures/p6_5` | Host allowlist, timeout, bounded retries, 2 MB capture limit; live smoke separate |
| Raw artifact storage | Preserve bytes before parsing | Existing filesystem + atomic `os.replace` | YES | YES | NO | YES | Replay and hash verification | repository/product artifact root | Safe artifact IDs; root containment; no source execution |
| PostgreSQL migration verification | Validate target schema | Docker `postgres:16-alpine`, `psql` in container | YES | YES | NO | YES (runtime image available) | Exercises production-target SQL without host install | `migrations/001_p6_5_understanding.sql`, gate script | Ephemeral named container; no credentials committed |
| SQLite deterministic adapter | Fast constraint/repository tests | Python `sqlite3` | YES | YES | NO | YES | Reproduces FK/unique/query behavior offline | `SQLiteUnderstandingRepository`, `tests/p6_5` | Fixed parameterized SQL; explicitly not production authority |
| P6 typed quant gateway | Run one event-scoped experiment | Existing `P6QuantGateway`, `TypedToolRequest` | YES | YES | NO | YES | Reuses frozen ResearchRun/QuantRun/Artifact contracts | `UnderstandingEngine._run_quant` | Gateway validation, no arbitrary SQL/tools, provenance required |
| P6 learning state | Persist learning encounter | Existing `LearningStore`, `LearningCard` | YES | YES | NO | YES | Closes the understanding-to-learning loop | `p6_5.product` | Card carries evidence/limitations; no invented answer key |
| Codex app/workspace tools | Inspect local task/artifacts when needed | `mcp__codex_app__*` | YES | YES | NO | YES | Workspace navigation and artifact support | task operations only | No external source authority; tool calls remain user-scoped |
| a-stock-data | A-share source discovery review | Public GitHub repository/skill-style material | YES (research access) | NO for facts | NO | NO | Identify possible underlying sources and field mappings only | `A_STOCK_DATA_DISCOVERY_REVIEW.md` (separate audit) | Discovery output cannot enter canonical FACT claims |
| AKShare | Adapter/discovery candidate review | Public project/documentation | YES (research access) | NO for facts | NO | NO | Coverage exploration and cross-source comparison only | admission review (separate audit) | Endpoint/source-family admission required; no silent authority |
| Tushare Pro | Tier-1 provider candidate review | Public documentation | YES (research access) | NO pending admission | NO | NO | Evaluate token, licence, PIT and revision requirements | admission review (separate audit) | No token hardcoded; no production ingestion in P6.5 |
| PostgreSQL Python driver | Direct production repository | `psycopg`/SQLAlchemy | NO | NO | NO | NO | Not needed for migration verification or deterministic adapter | deferred | Do not install merely to satisfy an unimplemented production path |
| New plugin/MCP server | External integrations | None required | NO | NO | NO | NO | No capability gap justified it | nowhere | Installation would expand trust and network surface without need |
| New Python dependency | P6.5 runtime | None required | NO | NO | NO | NO | Existing stack and stdlib cover the slice | dependency audit | Dependency lock remains unchanged |
| Unrestricted HTTP/scraping | Broad source collection | None | NO | NO | NO | NO | Outside scope and unsafe | nowhere | Explicitly prohibited |
| LLM-generated SQL / dynamic execution | Autonomous data access | None | NO | NO | NO | NO | Violates typed boundary | nowhere | Explicitly rejected by security tests |
| Trading/broker/automatic recommendation | Production action | None | NO | NO | NO | NO | P6.5 is an understanding slice, not an execution system | nowhere | Out of scope and gated |

## Installation decision

The audit found no trusted capability gap that warrants installation. No new
plugin, MCP server, Python package, agent framework, provider SDK, host database,
or secret was installed for P6.5. The existing Docker image is used only as an
ephemeral migration-verification fixture. Candidate source projects are
documented separately and remain below the Source Admission boundary.
