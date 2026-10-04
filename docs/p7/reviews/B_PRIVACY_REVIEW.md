# P7 Independent Review B — Privacy and Ownership

**Review date:** 2026-10-03  
**Track:** B — private data, ownership, projection, and revocation  
**Decision:** **PASS — bounded local P7 slice; not production approval**

## Review scope

This pass applies the privacy matrix: users cannot read or edit another user's
private graph, projections expose only selected fields, revocation stops future
access while the private source survives, attachments do not bypass room
permissions, and authorized context is owner scoped.

## Evidence inspected

- `SQLiteP7Repository._principal` rejects missing, revoked, suspended, deleted,
  and expired sessions before owner-scoped operations.
- Node, edge, mastery, thread, context, export, deletion, room, post, comment,
  projection, and attachment methods all use the authenticated principal.
- Projections require consent, an owned/current fingerprint, allow-listed fields,
  version, and limitations; stale/revoked projections are not readable.
- `delete_personal` removes private graph/mastery rows, revokes projections,
  and records an audit event. Model payloads are canonical JSON.

## Fresh command evidence

- Requested baseline: `pytest -q tests/p7` **29 passed** and the paired full
  suites **244 passed, 1 skipped** in each environment.
- Current expanded adversarial run: **29 P7 passed** and both full suites
  **244 passed, 1 skipped**.
- `make p5-5-gate` and the migration/PostgreSQL schema gate pass.

## Local-slice acceptance

Cross-user reads/edits, consent and field filtering, revocation/source
retention, context/export/delete, membership, stale projections, expired and
suspended sessions, revoked sessions, duplicate IDs, and cross-owner edges are
covered by the focused and adversarial tests. The local privacy boundary is
therefore accepted for the bounded P7 slice.

## Residual production risks (non-blocking for this bounded slice)

- A production identity provider, session issuance, key rotation, and audit
  retention policy are not integrated with this local repository.
- History, artifact-link, and audit rows are intentionally retained after
  deletion; deployment must document retention, operator access, and erasure
  guarantees.
- Composite owner-aware database keys and projection room/group binding should
  be added before multi-tenant PostgreSQL deployment.
- Source authority resolution and mandatory limitations policy need an adapter
  to the P4–P6.6 artifact registries, rather than caller-supplied IDs alone.

Privacy passes for the bounded local P7 slice; residuals remain production
hardening work, not local-gate blockers.
