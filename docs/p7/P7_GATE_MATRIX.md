# P7 Requirement-to-Evidence Gate Matrix

The matrix is the bounded local P7 acceptance record. “PASS” means the
behavior is tested or the migration/command is checked; hosted operations and
moderation remain P8 readiness risks.

| # | Requirement | Evidence | Status |
|---:|---|---|---|
| 1 | typed principal | `models.py`, P7 tests | PASS |
| 2 | active session | `_principal`, lifecycle test | PASS |
| 3 | expiry/revocation | adversarial test | PASS |
| 4 | suspended principal | adversarial test | PASS |
| 5 | private node default | migration/model | PASS |
| 6 | owner-scoped node read | privacy test | PASS |
| 7 | owner-scoped update | privacy test | PASS |
| 8 | duplicate node rejection | adversarial test | PASS |
| 9 | typed graph edge | models/migration | PASS |
| 10 | cross-owner edge rejection | adversarial test | PASS |
| 11 | learning thread ordering | vertical slice | PASS |
| 12 | research history | vertical slice | PASS |
| 13 | strategy history contract | `P7_STRATEGY_HISTORY.md` | PASS |
| 14 | mastery evidence types | model/migration | PASS |
| 15 | incorrect → review | community test | PASS |
| 16 | evidence explanation | mastery test | PASS |
| 17 | owner-scoped mastery | repository | PASS |
| 18 | bounded authorized context | privacy test | PASS |
| 19 | explicit projection consent | projection test | PASS |
| 20 | allow-listed fields | projection test | PASS |
| 21 | current fingerprint | repository | PASS |
| 22 | projection version | migration/model | PASS |
| 23 | projection visibility | migration/model | PASS |
| 24 | public read boundary | repository | PASS |
| 25 | room read boundary | membership test | PASS |
| 26 | projection revocation | projection test | PASS |
| 27 | source survives revoke | projection test | PASS |
| 28 | stale projection marking | vertical slice | PASS |
| 29 | room creation | community test | PASS |
| 30 | membership join | community test | PASS |
| 31 | removed membership denial | adversarial test | PASS |
| 32 | claim labels | model/migration | PASS |
| 33 | author-only attachment | community test | PASS |
| 34 | active projection attachment | repository | PASS |
| 35 | save-as-private-question | repository/docs | PASS |
| 36 | comments are typed data | model validation | PASS |
| 37 | parameterized SQL | injection test/review | PASS |
| 38 | audit publication/revocation | repository | PASS |
| 39 | bounded export | export test | PASS |
| 40 | canonical export fingerprint | adversarial test | PASS |
| 41 | deletion revokes projections | repository | PASS |
| 42 | deletion removes private graph | vertical slice | PASS |
| 43 | additive SQLite/PostgreSQL migration | disposable migration gate | PASS |
| 44 | dual-environment/reproducible gate | `make p5-5-gate`, full suites | PASS |

The matrix does not claim production availability. Backup/restore, abuse
moderation, rate limiting, encrypted operational storage, and hosted identity
remain explicit P8 readiness work.

## Mission section 85 traceability (44 gates)

The following list is the exact mission-level gate order. Evidence is local and
deterministic; a PASS never means that a hosted control has been deployed.

| # | Mission gate | Evidence | Status |
|---:|---|---|---|
| 1 | P6.6 final gate | final validation commands and provenance probe | PASS |
| 2 | private knowledge graph | typed nodes/edges and migration 003 | PASS |
| 3 | private by default | `privacy_scope=PRIVATE`, projection consent | PASS |
| 4 | explicit ownership | session principal checks and cross-owner tests | PASS |
| 5 | typed mastery evidence | `MasteryEvidence` model/table | PASS |
| 6 | explainable mastery | deterministic state explanation and evidence IDs | PASS |
| 7 | misconception continuity | `personal.py`, lifecycle test | PASS |
| 8 | learning threads | ordered thread items and export | PASS |
| 9 | research history | fingerprinted history rows and timeline | PASS |
| 10 | strategy history | `p7_strategy_versions`, feature/backtest/OOS/paper linkage | PASS |
| 11 | personal timeline | bounded owner-scoped `TimelineEvent` service | PASS |
| 12 | evidence-grounded guidance | optional `EvidenceGroundedGuidance` | PASS |
| 13 | personalization boundary | guidance cannot mutate truth or quantitative records | PASS |
| 14 | community rooms | membership and active-room controls | PASS |
| 15 | evidence-linked posts | typed claims, attachments, projection allow-list | PASS |
| 16 | research sharing | event/strategy projection contracts preserve provenance | PASS |
| 17 | strategy projection | strategy artifact fingerprint + version linkage | PASS |
| 18 | public projection | public visibility read boundary | PASS |
| 19 | private source retention | revoke leaves private source nodes intact | PASS |
| 20 | revocation | revoked/stale projections fail closed | PASS |
| 21 | cross-user controls | owner/session/room adversarial tests | PASS |
| 22 | agent context authorization | bounded `authorized_context` owner scope | PASS |
| 23 | prompt injection defense | sanitizer detects and redacts injected directives | PASS |
| 24 | inert community content | sanitizer returns data-only envelope; no dispatcher | PASS |
| 25 | shared research limitations | projections carry limitations and fingerprints | PASS |
| 26 | strategy vertical slice | `test_p66_strategy_vertical.py`: real LabRun→mastery→thread→projection→post→question | PASS |
| 27 | real-event learning slice | `test_real_event_learning_journey.py`: BLS ProductJourney→Event/Evidence/Concept/mastery/history | PASS |
| 28 | privacy review | `P7_PRIVACY_REVIEW.md` and audit register | PASS |
| 29 | security review | `P7_SECURITY_REVIEW.md`, adversarial tests | PASS |
| 30 | community integrity review | `community.py`, claim/summary tests | PASS |
| 31 | research integrity review | provenance/limitations and P6.6 gate | PASS |
| 32 | learning integrity review | explicit outcomes and correction lifecycle | PASS |
| 33 | data quality review | `P7_DATA_QUALITY_REVIEW.md` and owner checks | PASS |
| 34 | reproducibility review | `P7_REPRODUCIBILITY_REVIEW.md` and dual runs | PASS |
| 35 | no regression | full P4–P6.6 suite | PASS |
| 36 | full suite | `.venv` and `.venv-quant` pytest | PASS |
| 37 | Ruff | `ruff check src tests scripts` | PASS |
| 38 | notebook | `make p5-5-gate` notebook step | PASS |
| 39 | governance | `validate_governance.py` | PASS |
| 40 | pip integrity | both environment `pip check` | PASS |
| 41 | PostgreSQL | disposable migration/schema gate | PASS |
| 42 | diff check | `git diff --check` | PASS |
| 43 | clean worktree | post-commit status check | PASS |
| 44 | provenance | committed HEAD and stable export fingerprint | PASS |
