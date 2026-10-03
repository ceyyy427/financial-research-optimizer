# F — Product Truth Review

**Review date:** 2026-10-03  
**Scope:** P7 product meaning, evidence authority, user journeys, and the
no-advice boundary for the bounded local slice.

## Review question

Does the proposed P7 product help a person build a traceable understanding from
research evidence while preserving the existing quantitative and factual
authorities? A passing product must support both planned journeys:

`strategy -> personal continuity -> optional community projection -> new question`

and

`CPI event -> personal learning -> optional community projection`.

It must keep quantitative results, provenance, limitations, and source labels
immutable and must not turn discussion or guidance into investment advice.

## Authorities and product truth

| Boundary | Required behavior | Current evidence | Review state |
| --- | --- | --- | --- |
| Quantitative truth | Reuse P4/P5/P5.5/P6.6 artifacts and fingerprints; P7 does not recalculate results. | `docs/p7/P7_ARCHITECTURE.md:25-37`, `src/finahinking/p6_6/` | PASS for bounded references |
| Factual truth | Preserve P6.5 source, claim, evidence, and limitation labels. | `docs/p7/P7_ARCHITECTURE.md:29-33` | PASS for bounded references |
| Personal continuity | Store owner-scoped relationships and evidence-derived mastery, with explanations. | `src/finahinking/p7/models.py:32-133`, `src/finahinking/p7/repository.py:122-238`, migration 003 | PASS in local SQLite vertical slice |
| Community truth | Publish only an explicit, versioned, allowlisted projection. | `src/finahinking/p7/models.py:135-166`, `src/finahinking/p7/repository.py:248-413`, `docs/p7/P7_ARCHITECTURE.md:54-70` | PASS for consent/revoke/room slice |
| Advice boundary | Guidance may change explanation depth, never factual or quantitative payloads. | `docs/p7/P7_ARCHITECTURE.md:49-52`; P6.6 limitations | PASS; no advice path is present |

## Findings

1. The typed model layer is directionally consistent with product truth. Private
   nodes are restricted to `PRIVATE`, payloads are JSON-safe and bounded, and
   mastery state carries evidence IDs and an explanation (`models.py:20-61,
   102-117`). These are useful contracts, not proof of a working journey.

2. The current tree has a SQLite repository and public exports. It supports
   owner-scoped nodes, mastery derivation, projections, rooms, posts, bounded
   context, export, deletion, and save-as-question (`src/finahinking/p7/repository.py`).
   The planned workflow/product modules and a runnable end-to-end strategy/CPI
   journey are outside this adapter. Production UI, hosted identity, and social-network operations are
   outside this bounded local slice and remain P8 decisions.

3. The current eight-test P7 repository and vertical slice collects and passes. Those tests
   cover owner scoping, evidence-derived NEEDS_REVIEW, consent/sanitization,
   revocation, room membership, bounded context, export, and SQL metacharacter
   handling. They do not yet prove either complete product journey or a real
   UI/CLI interaction; those are P8 product-surface work.

4. Product claims must remain descriptive. P6.6 reports explicitly bound
   historical evidence and list survivorship, market-impact, and prospective
   uncertainty limitations. A P7 product surface must display those limits next
   to a result and projection; a title or community post cannot silently turn a
   historical finding into a forecast.

## Evidence ledger

The following commands are the minimum evidence to attach before a product
truth decision is made:

| Evidence | Command or artifact | Expected evidence |
| --- | --- | --- |
| P6.6/P7 local authority | `./.venv/bin/python -m pytest -q tests/p6_6 tests/p7` | Focused P6.6/P7 tests pass |
| P7 repository and vertical slices | `./.venv/bin/python -m pytest -q tests/p7` | 11 tests pass against SQLite |
| Dual full regression | `./.venv/bin/python -m pytest -q`; `./.venv-quant/bin/python -m pytest -q` | Both report 226 passed, 1 skipped |
| Migration authority | `./scripts/verify_p6_5_postgres.sh` | Migrations 001, 002, and 003 apply; PostgreSQL schema gate reports PASS |
| No advice / limitation display | Product journey test plus exported record inspection | Limitations, provenance, and claim labels remain visible and unchanged |
| Current baseline probe | `./.venv/bin/python -m pytest -q tests/p7` | Current bounded slice passes |

## Decision

**PASS — bounded local P7 product-truth slice (not production).** The eleven P7 tests, dual full
suites, and migration gate support the local evidence-first boundary. Production
UX, moderation, hosted identity/recovery, and service-scale claims remain
explicit P8 residual risks.
