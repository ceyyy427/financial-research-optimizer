# P6.5 Evaluation Plan

## Evaluation principle

The gate evaluates whether the product improves evidence-bound reasoning, not
whether it produces a more confident summary or more engagement. Checks are
deterministic wherever possible; live network smoke is a separately labelled
observation. A failed check is a rework signal, not a reason to relax a contract.

## Test layers

| Layer | What it proves | Current evidence |
| --- | --- | --- |
| Canonical model | IDs, enums, finite values, fingerprints, JSON-safe records | `tests/p6_5/test_models.py` |
| Source admission/temporal | tier decisions, timezone/order, missing availability, revisions/conflicts | `test_admission_temporal.py` |
| BLS capture/replay | allowlist, bounded transport, exact observed response shape, hash/replay, quarantine | `test_bls_adapter.py`, committed fixture |
| Data quality | declared grain, duplicates, required fields, numeric validity, temporal validity | `DataQualityReport.from_rows`, security/quality tests |
| SQL/repository | migration, FKs/unique checks, raw artifact write, parameterization, Show Evidence | `test_repository.py`, Docker PostgreSQL migration check |
| Claims/evidence | trusted fingerprint resolution, status/type distinctions, evidence projection | `test_claims_knowledge.py` |
| Product journey | event → mechanism → evidence → typed quant → ladder → P6 explanation → learning | `test_product_journey.py` |
| Security | source prompt injection is data, unsafe URI/SQL/Jinja payloads rejected, no dynamic execution | `test_security_quality_evaluation.py`, AST scan |
| Regression | P0–P6 contracts and provenance remain valid | full existing suite and both environments |

## Data-quality contract

`DataQualityReport` checks:

- row count and declared logical grain;
- missing required fields (reported by field, never silently imputed);
- duplicate grain keys;
- non-finite/non-numeric declared numeric fields;
- impossible publication/availability/retrieval ordering;
- a `passed` flag and machine-readable issue list.

The report diagnoses the captured rows. It never changes a source value, turns
`"-"` into zero, or declares a provider authoritative.

## Understanding gain metric

The first metric is a transparent pre/post proxy over a fixed set of questions:

```text
correct_before = sum(pre_answers)
correct_after  = sum(post_answers)
gain           = correct_after - correct_before
```

The output includes item count, interpretation, and the limitation that there
is no randomized control, correction for retest/selection effects, or causal
treatment estimate. Future studies should include fact understanding, mechanism
understanding, evidence interpretation, uncertainty, and transfer—not only
engagement. Misconceptions to test include “hot CPI means stocks must fall,”
“correlation proves causality,” “a low p-value proves a theory,” “historical
profitability predicts future profitability,” and “historical analogues determine
the next outcome.”

## Independent A–K audit plan

| Pass | Question | Evidence to inspect |
| --- | --- | --- |
| A Architecture | Does P6.5 consume rather than duplicate P6? | imports, gateway call, frozen tests |
| B Source integrity | Is BLS the original admitted source and identity preserved? | source/endpoint/release, raw capture, admission docs |
| C Temporal integrity | Are five clocks explicit and ordered? | model/parser tests, timing rows |
| D Data quality | Are grain, missingness, duplicates, and quarantine visible? | fixture and quality report |
| E Database | Do migration constraints and parameterized methods hold? | SQLite + Docker PostgreSQL output |
| F Claim grounding | Does every trusted claim resolve to evidence/fingerprint? | issuer, bundle, Show Evidence tests |
| G Quant | Does Event → Quant use the approved typed gateway? | request/provenance/result fingerprint |
| H Explanation | Are fact, interpretation, hypothesis, unknown, limitation distinct? | claim statuses, ladder, product fields |
| I Learning | Does the card/state reuse the same grounded evidence? | card context, LearningStore encounter |
| J Security | Are SQL, tool, source, and prompt boundaries closed? | payload rejection, AST, artifact path tests |
| K Reproducibility | Can the fixture replay to stable hashes/results? | capture hash, fingerprints, offline tests |

## Gate commands

The final gate should run, from the repository root:

- `.venv/bin/pytest -q`;
- `.venv-quant/bin/pytest -q`;
- `ruff check .`;
- repository-native notebook and governance validators;
- `.venv/bin/python -m pip check` and `.venv-quant/bin/python -m pip check`;
- Docker PostgreSQL migration verification with `psql`;
- AST/security scan and replay/fingerprint checks;
- `git diff --check` and `git status --short`.

The exact command names for notebook/governance validators remain those already
used by the P0–P6 gates; P6.5 must not replace them with a weaker local check.
After the implementation commit, assert every successful workflow response’s
`provenance.code_commit` equals `git rev-parse HEAD`.

## Pass/fail criteria

P6.5 passes only when the existing P6 suite remains valid, no unnecessary
capability was installed, one official BLS event is captured/replayable and
canonicalized, temporal/revision/conflict behavior is explicit, SQL and claim
boundaries hold, Show Evidence and the five-level ladder work, the typed quant
and learning bridges are grounded, and A–K audits have evidence. A live source
failure does not invalidate deterministic replay; a deterministic contract
failure cannot be excused by a successful live response.

The expected post-gate state is P6.5 complete with P7 waiting for explicit
human approval.
