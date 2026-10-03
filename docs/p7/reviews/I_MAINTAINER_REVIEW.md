# I — Maintainer and Engineering Review

**Review date:** 2026-10-03  
**Scope:** Package boundaries, public API discoverability, tests, documentation,
dependency/capability discipline, change ownership, and release hygiene.

## Review question

Could a maintainer understand, test, review, release, and later change P7
without guessing which module owns identity, persistence, projection, or
product behavior? This review covers the bounded local foundation, not a
hosted-production release.

## Findings

1. P7 has explicit exports and a SQLite repository in
   `src/finahinking/p7/{__init__,models,repository}.py`. The repository keeps
   identity, private continuity, projection, community, export, and deletion
   behavior in one reviewable local adapter; future service decomposition is a
   P8 design choice, not a blocker for this slice.

2. The P7 suite collects and passes eight focused repository and vertical
   scenarios. They cover owner scoping, evidence-derived mastery,
   consent/sanitization, revocation, room membership, bounded context,
   export/delete behavior, and SQL metacharacters. Broader hosted UX,
   moderation, and product-journey coverage remains P8 follow-up work.

3. The typed models have useful local discipline: frozen dataclasses,
   allowlisted node/relation/claim/status values, bounded JSON payloads, and
   private-default scope. Repository methods repeat authorization checks rather
   than trusting model fields. Comment validation and progressive-disclosure
   UI hardening are explicit P8 UX items.

4. The P7 capability matrix records no installation gap and correctly defers
   graph/vector databases, moderation SaaS, brokers, and external connectors.
   Maintainers should preserve that dependency decision and add no package
   until a measured, reviewed gap exists.

5. The local evidence is reproducible: both full environments report 223
   passed and 1 skipped, Ruff and governance checks are clean, and the
   disposable PostgreSQL gate applies migration 003. A final release still
   needs the commit/provenance record and clean-worktree check; that release
   hygiene is a P8 follow-up, not a failure of the bounded local review.

## Evidence ledger

| Evidence | Command or artifact | Observed result |
| --- | --- | --- |
| API/import surface | `./.venv/bin/python -c "import finahinking.p7 as p; print(p.__all__)"` | Explicit supported P7 exports |
| P7 collection and behavior | `./.venv/bin/python -m pytest -q tests/p7` | **8 passed** |
| Dual full regression | `./.venv/bin/python -m pytest -q`; `./.venv-quant/bin/python -m pytest -q` | **223 passed, 1 skipped** in each environment |
| Static/governance quality | `./.venv/bin/ruff check src tests scripts`; `python3 scripts/validate_governance.py .` | PASS |
| Migration gate | `./scripts/verify_p6_5_postgres.sh` | Migration 003 applies; PostgreSQL gate PASS |
| Dependency policy | `git diff -- requirements.lock pyproject.toml DEPENDENCY_RECORD.md`; capability matrix review | No unapproved dependency or connector gap |

## Decision

**PASS — bounded local maintainer foundation (not production).** The explicit
API, eight P7 tests, dual full suites, lint/governance checks, and migration
003/PostgreSQL gate provide an evidence-backed local baseline. Hosted UX,
moderation/abuse controls, hosted recovery, and release automation remain
explicit non-blocking P8 residual risks.
