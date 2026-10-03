# H — Operations and Recovery Review

**Review date:** 2026-10-03  
**Scope:** Migration safety, SQLite/PostgreSQL parity, transaction behavior,
rollback, export/deletion recovery, observability, and the post-commit command
gate. P7 architecture deliberately limits this phase to a locally validated
research product; this review does not infer production availability.

## Review question

Can maintainers apply and verify the additive P7 schema without silently
changing P4–P6.6 evidence, and can they recover or delete private state with a
known result? Every operational claim identifies the migration, command, and
limitation.

## Current evidence

| Area | Current repository evidence | State |
| --- | --- | --- |
| Additive schema | `migrations/003_p7_personal_community.sql` defines principals, sessions, private nodes/edges, mastery, history, rooms, projections, posts, comments, attachments, and audit rows. | PASS in local migration path |
| Migration path | The SQLite repository applies migrations 001 → 002 → 003; `scripts/verify_p6_5_postgres.sh` applies and inspects all three migrations in a disposable PostgreSQL instance. | PASS; migration 003/PostgreSQL gate PASS |
| PostgreSQL check | The disposable gate checks P7 tables and indexes and prints `P6.5_POSTGRES_SCHEMA_PASS`. | PASS for the bounded schema gate |
| SQLite integrity | `SQLiteP7Repository` enables foreign keys, binds values, and wraps writes; P7 repository and vertical tests pass. | PASS for local slice |
| Recovery/deletion | Repository export/delete and projection revocation are exercised by the P7 vertical tests, including owner isolation and SQL metacharacters. | PASS for bounded local behavior |
| Production operations | Backups, restore/failover, hosted identity, retention, health/incident runbooks, and durable observability are not claimed by this phase. | P8 residual; not a local gate blocker |

## Findings

1. Migration 003 is additive in shape and is now exercised through both the
   SQLite path and the disposable PostgreSQL gate. The gate establishes schema
   application and required P7 tables/indexes; it is not evidence of hosted
   availability or a production backup strategy.

2. The architecture correctly says production identity, backups, availability,
   staffing, and scale are separate readiness decisions
   (`P7_ARCHITECTURE.md:93-102`). Those boundaries remain visible in operator
   documentation and are explicit P8 residual risks.

3. Export/deletion semantics cross private/community boundaries. The local
   repository tests cover owner-scoped export, deletion, projection revocation,
   and adversarial SQL input. Hosted recovery drills, retention policy, and
   incident procedures remain P8 work.

## Evidence ledger

| Evidence | Command or artifact | Observed result |
| --- | --- | --- |
| P7 focused suite | `./.venv/bin/python -m pytest -q tests/p7` | **8 passed** |
| Dual full regression | `./.venv/bin/python -m pytest -q`; `./.venv-quant/bin/python -m pytest -q` | **226 passed, 1 skipped** in each environment |
| PostgreSQL migration gate | `./scripts/verify_p6_5_postgres.sh` | Migrations 001, 002, and **003 apply; PostgreSQL gate PASS** (`P6.5_POSTGRES_SCHEMA_PASS`) |
| Static/governance checks | Ruff, governance validator, shell syntax, and `git diff --check` | PASS |
| Local recovery behavior | P7 export/delete, revoke, owner-isolation, and metacharacter tests | PASS for bounded local repository behavior |

## Decision

**PASS — bounded local operations and migration/recovery slice (not
production).** The eleven P7 tests, dual full suites (226 passed, 1 skipped),
and migration 003/PostgreSQL PASS establish the local evidence gate. Hosted
backup/restore/failover, retention, monitoring, incident response, and hosted
identity remain explicit non-blocking P8 residual risks.
