# P7.5 Product-Usable Gate — Final Validation Report

## Scope and decision

P7.5 is the additive Knowledge & Education Engine and local product slice.
P6.5, P6.6, and P7 remain the event, research, strategy, privacy, and
projection authorities. The local runtime is a loopback standard-library
service with SQLite/sample defaults and no real-money capability.

## 39-item gate

| # | Gate item | Evidence | Result |
|---:|---|---|---|
| 1 | P7 baseline valid | P7 regression, migration, provenance gates | PASS |
| 2 | Structured Knowledge Engine | `p7_5.knowledge`, catalog fingerprint, schema tests | PASS |
| 3 | Concept prerequisites | closure and cycle tests | PASS |
| 4 | Equations/derivations | typed records and multi-step tests | PASS |
| 5 | Code examples linked | every reference concept has a code contract | PASS |
| 6–8 | Finance, quant, strategy links | typed application links and tests | PASS |
| 9 | Learning paths | four typed paths and exact reference order | PASS |
| 10–11 | Personal mastery/misconceptions | Knowledge self-check writes catalog-keyed P7 mastery evidence; P7 misconception service remains the correction authority | PASS (bounded) |
| 12 | Supported local launch | `scripts/run_local_app.py`, console entry point | PASS |
| 13–14 | First-run/sample mode | source clean-install smoke, fixture route | PASS |
| 15–21 | Event/knowledge/quant/strategy/paper/personal/community journeys | Full ProductJourney projection, real LocalResearchService artifacts, paper-only strategy, explicit community projection route, `tests/p7_5/test_product_gate_real.py` | PASS |
| 22 | Save/reopen | SQLite restart test plus persistent `/api/research/artifacts/{id}` reopen | PASS |
| 23 | Local diagnostics | `/diagnostics`, `/api/diagnostics`, redacted `/api/diagnostics/bundle`, and private `/api/personal/backup` | PASS |
| 24 | Secrets safe | `scripts/secret_scan.py`, no provider key in sample mode | PASS |
| 25 | Real-money execution absent | no broker/order route; strategy `real_money=false` | PASS |
| 26 | Accessibility | semantic HTML, skip link, labels, focusable links/buttons, no-script forms | PASS (bounded) |
| 27 | Security | loopback-only binding, exact-origin check, protected form CSRF, CSP, headers, body cap, parameterized SQL | PASS (bounded) |
| 28 | E2E | HTTP smoke plus event-learning, concept mastery, quant artifact, strategy OOS/paper, projection tests | PASS |
| 29 | P4–P7 regression | full suite in both environments | PASS |
| 30 | Full suite | `.venv`: 272 passed, 1 skipped; quant/research runtime, restart, backup, and diagnostics tests included | PASS |
| 31 | Ruff | `ruff check src tests scripts` | PASS |
| 32 | Notebook | `make notebook-check` | PASS |
| 33 | Governance | `scripts/validate_governance.py .` | PASS |
| 34 | PostgreSQL migration | `scripts/verify_p6_5_postgres.sh` | PASS |
| 35 | pip | `pip check` in both environments | PASS |
| 36 | Build smoke | `pip wheel --no-deps --wheel-dir dist .` | PASS |
| 37 | Diff check | `git diff --check` | PASS |
| 38 | Clean worktree | `git status --short` clean at local release tag `v0.1.0` | PASS |
| 39 | Provenance alignment | local release tag `v0.1.0`, source fingerprints, and fixture hash | PASS |

## Independent reviews

Reviews A–J are in `docs/p7_5/reviews/`. The catalog audit covers knowledge,
education, quant/strategy, and reproducibility; the remaining reviews cover
product architecture, UX, privacy, local-first operation, accessibility, and
security.

## Gate decision

**P7.5 Product-Usable Gate: PASS for the bounded local product slice**, after
the command evidence is rerun at the delivery commit. The next phase is the P8
source-distribution public-beta gate; cloud sync, hosted accounts, brokers, and
real-money work are explicitly stopped.
