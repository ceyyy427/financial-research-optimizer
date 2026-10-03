# G — Community and UX Review

**Review date:** 2026-10-03  
**Scope:** Research Room behavior, projection consent and revocation, typed
discussion, evidence quality, moderation, progressive disclosure, and user
control for the bounded local slice.

## Review question

Can a person understand exactly what is private, what is shared, which evidence
supports a post, and how to stop sharing? The community surface must be a typed
research conversation rather than a popularity feed. It must preserve
attribution, uncertainty, disagreement, limitations, and an explicit
save-as-question action.

## Contract review

| UX promise | Required behavior | Current evidence | State |
| --- | --- | --- | --- |
| Private by default | A source object is never attached directly; owner selects fields and visibility. | `docs/p7/P7_ARCHITECTURE.md:54-64`; `ProjectionSpec` in `models.py:135-155`; `repository.py:260-286` | PASS in SQLite slice |
| Consent and preview | User sees an allowlisted projection before publishing and must consent. | `tests/p7/test_personal_community.py:60-76`, `repository.py:260-286` | PASS for repository consent; hosted UX deferred |
| Revocation | Old attachments become unreadable while private source survives. | `tests/p7/test_personal_community.py:73-78`, `repository.py:312-331` | PASS in local slice |
| Claim typing | Posts identify fact, interpretation, hypothesis, quantitative finding, unknown, or limitation. | `CommunityPost`, migration 003 checks, `repository.py:366-384` | PASS for typed local path |
| Membership | Room reads/writes and attachments require active membership and role. | `tests/p7/test_personal_community.py:81-100`, `repository.py:333-407` | PASS in local slice |
| Quality and moderation | Summaries expose agreement/disagreement, support/counter-evidence, unknowns, and testable questions; moderation handles abuse and overclaims without silencing disagreement. | `docs/p7/P7_ARCHITECTURE.md:66-70` | P8 residual; not required for bounded local PASS |

## Findings

1. The intended UX contract is unusually clear about consent, revocation, and
   claim labels. `ProjectionSpec` requires fields, visibility, source identity,
   fingerprint, and version. The repository enforces the allowlist for the
   SQLite slice, but there is no dedicated preview builder or user-facing
   projection surface.

2. `CommunityComment` has no validation hook in `models.py:200-207`, while
   `CommunityPost` validates claim type and status. Empty or malformed comment
   content can therefore reach `repository.py:399-407` unless the repository
   validates it. This is a P8 hosted-UX hardening item, not a blocker for the
   bounded repository gate.

3. No user-facing interface, CLI, or deterministic demo currently shows a
   Personal Home, timeline, projection preview, room discussion, or revoke
   action. The architecture explicitly calls for repository-native interfaces
   and real integration tests (`P7_ARCHITECTURE.md:93-102`), so presentation
   prose cannot substitute for interaction evidence.

4. The current eight P7 tests are a useful SQLite acceptance slice covering private
   nodes, mastery, consent, sanitization, revocation, room membership, export,
   and SQL metacharacters. It passes, but it does not cover moderation,
   summaries, malicious links, prompt injection, stale attachments, or a
   progressive-disclosure interface. Hosted UX, moderation, and abuse workflows
   remain outside the bounded local gate.

## Evidence ledger

| Evidence | Command or artifact | Expected evidence |
| --- | --- | --- |
| P7 community regression | `./.venv/bin/python -m pytest -q tests/p7` | 8 local scenarios pass without authorization-bypassing mocks |
| Dual full regression | `./.venv/bin/python -m pytest -q`; `./.venv-quant/bin/python -m pytest -q` | Both report 226 passed, 1 skipped |
| Migration boundary | `./scripts/verify_p6_5_postgres.sh` | PostgreSQL applies and inspects migration 003 successfully; gate reports PASS |
| UX/moderation follow-up | Hosted preview, malicious-link, abuse, and HTML/prompt-injection tests | P8 residual evidence; not a local P7 gate requirement |

## Decision

**PASS — bounded local community/projection slice (not production).** Consent,
revocation, membership, labels, and save-as-question behavior are covered by
the eight P7 tests. Hosted UX, moderation/abuse workflows, attributed
summaries, hosted recovery, and production community operations remain explicit
non-blocking P8 residual risks.
