# P7.5 Capability Matrix

| Capability | Authority / implementation | Evidence | Status |
| --- | --- | --- | --- |
| P7 baseline | P7 repository, migration, privacy tests | P7 regression and deletion test | PASS |
| Structured knowledge | `finahinking.p7_5.knowledge` | typed catalog tests | PASS |
| Minimum knowledge domains | `DomainCoverage` map (17 domains) | domain coverage test/schema | PASS |
| Prerequisites and paths | `KnowledgeCatalog` | closure/cycle/path tests | PASS |
| Equations and derivations | `Equation`, `DerivationStep` | concept contract tests | PASS |
| Data→math→code→finance | typed application links | knowledge tests/docs | PASS |
| Local launch | `finahinking.local_app`, `scripts/run_local_app.py` | HTTP smoke | PASS |
| SQLite/sample mode | P7 migration + captured fixtures | diagnostics/E2E | PASS |
| Event/quant/strategy worlds | P6.5/P6.6 adapters and summaries | journey tests | PASS |
| Personal/community boundary | P7 repository and projections | privacy/E2E tests | PASS |
| Save/reopen | SQLite file mode | restart journey | PASS |
| Accessibility baseline | semantic landmarks, skip link, visible status | accessibility review | PASS |
| Security baseline | loopback, CSP, no secrets, no order endpoint | security review | PASS |
| Reproducibility | deterministic catalog, fixtures, fingerprints | provenance and clean install | PASS |
| Optional plugins | No capability gap: stdlib shell, existing engines, pytest/Ruff, and CUA/browser smoke cover the gate | capability audit and dependency record | NO INSTALL REQUIRED |

The detailed 39-item Product-Usable Gate is recorded in
`P7_5_FINAL_VALIDATION_REPORT.md`; each row links to a fresh command or an
explicit documented conditional.
