# P7 Independent Review E — Reproducibility

**Review date:** 2026-10-03  
**Track:** E — deterministic persistence, lineage, replay, and release evidence  
**Decision:** **PASS — bounded local P7 slice; not production approval**

## Review scope

This pass checks canonical payloads, owner-safe export, source fingerprints,
migration parity, dependency reproducibility, and dual-environment release
commands. It does not claim a production backup/restore or hosted replay
service.

## Evidence inspected

- P7 keeps P4–P6.6 as authorities and stores source kind/id/fingerprint rather
  than recalculating earlier research or strategy outputs.
- Sorted-key JSON, `export_personal`, `validate_export_fingerprint`, source
  limitations, optional code commit, and projection version fields provide a
  deterministic local envelope.
- `requirements.lock` uses exact package pins, including
  `setuptools==80.9.0`, matching the build-system pin; no new P7 dependency is
  declared.
- Migration 003 is loaded by the additive sequence and passes the disposable
  PostgreSQL schema check.

## Fresh command evidence

- Requested baseline: `tests/p7` **8 passed**; `.venv` and `.venv-quant` each
  **223 passed, 1 skipped**. Current adversarial expansion is **11 P7 passed**
  and **226 passed, 1 skipped** in both environments.
- `make p5-5-gate` passes full tests, Ruff, notebook, governance, both pip
  checks, and the quant smoke fingerprint.
- `bash scripts/verify_p6_5_postgres.sh` reports
  `P6.5_POSTGRES_SCHEMA_PASS` after migrations 001/002/003.

## Local-slice acceptance

The bounded local slice has canonical, tamper-evident export; reproducible
dependency/runtime checks in both environments; deterministic migration
application in SQLite and PostgreSQL schema verification; and no new runtime
dependency. Reproducibility passes for this scope.

## Residual production risks (non-blocking for this bounded slice)

- There is no import/replay API or encrypted backup/restore workflow; a
  production continuity service needs round-trip and disaster-recovery tests.
- The lock has exact versions but not per-artifact hashes/platform markers, and
  editable extras retain version ranges. Capture a hermetic build/SBOM before
  release.
- The PostgreSQL helper verifies schema objects, not the full repository
  behavior under concurrent production load. Add adapter-level integration and
  migration rollback tests.
- The shared worktree remains a development state until implementation, tests,
  migration, docs, and provenance are committed and `code_commit == HEAD` is
  recorded for every linked authority.

Reproducibility passes for the bounded local P7 slice; residuals are required
for production release sign-off but do not block Stage B local work.
