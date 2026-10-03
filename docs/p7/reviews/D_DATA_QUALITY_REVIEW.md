# P7 Independent Review D — Data Quality and Integrity

**Review date:** 2026-10-03  
**Track:** D — typed records, evidence quality, lineage, and relational integrity  
**Decision:** **PASS — bounded local P7 slice; not production approval**

## Review scope

This pass checks evidence-driven mastery, source fingerprints and limitations,
allow-listed/versioned projections, labeled community claims, duplicate/orphan
handling, and owner-scoped relational writes.

## Evidence inspected

- Models constrain node, relation, evidence, mastery, projection, and claim
  vocabularies and canonicalize JSON payloads.
- `save_mastery_evidence` persists evidence and recomputes state, count, exact
  evidence IDs, and explanation; the focused tests exercise incorrect and
  successful learning paths.
- Projections preserve source fingerprint, selected fields, version,
  limitations, consent, visibility, stale status, and revocation.
- `export_personal` emits stable ordering and an integrity-checkable
  `export_fingerprint`; the migration has keys, checks, uniqueness, FKs, and
  owner indexes.

## Fresh command evidence

- Requested baseline: **8 P7 passed** and both full environments **226 passed,
  1 skipped**; current expanded adversarial run is **11 P7 passed** and
  **226 passed, 1 skipped** in each environment.
- `make p5-5-gate` passes; PostgreSQL applies and checks migrations 001–003.

## Local-slice acceptance

The bounded slice rejects duplicate IDs and cross-owner graph writes, derives
mastery from persisted evidence, filters projection fields, records
limitations/fingerprints, marks changed sources stale, preserves claim labels,
and exports a tamper-evident private record. Data quality passes for this
tested local contract.

## Residual production risks (non-blocking for this bounded slice)

- `evidence_ids` and owner relationships are partly JSON/application
  invariants; composite owner-aware FKs and direct-SQL integrity tests would
  strengthen a multi-tenant production schema.
- Artifact/history source IDs still need a registry-backed authority resolver,
  verified code commit, dependency/configuration fingerprint, and source
  limitations policy.
- Mastery semantics need broader product validation for neutral evidence,
  repeated corrections, calibration, and model/version changes.
- Community counter-evidence, attributed summaries, moderation metrics, and
  quality reporting are outside the bounded Stage B persistence slice.

Data quality passes for the bounded local P7 slice; these are production
hardening and product-evaluation residuals.
