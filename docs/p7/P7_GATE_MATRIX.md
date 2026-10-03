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
