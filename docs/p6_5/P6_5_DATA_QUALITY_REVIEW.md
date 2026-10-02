# P6.5 Data Quality Review

## Scope

This review evaluates the admitted BLS CPI fixture and the deterministic
canonicalization path. It covers identity, grain, schema, required fields,
duplicates, temporal ordering, revision representation, missingness, numeric
validity, raw/canonical reconciliation, and persistence checks. It does not
claim that a single captured response proves the quality of all BLS history or
of any future provider.

## Quality contract

The adapter follows a fail-or-quarantine policy:

* A transport failure, non-UTF-8 payload, non-success BLS status, invalid JSON,
  or response-shape drift raises `BLSQuarantineError`.
* An unadmitted series, missing/non-numeric value, invalid month, or duplicate
  logical key is retained in the `quarantined` collection with a reason and
  footnotes where available. It is not silently discarded.
* `BLSParseResult.input_rows`, `admitted_rows`, and `reconciled` make the
  accounting explicit.
* `DataQualityReport` independently records row count, declared grain,
  missingness by field, numeric-invalid rows, temporal-invalid rows, duplicate
  grain keys, issues, and a boolean `passed` result.

This means a green parser test is evidence that the declared contract was
applied to the fixture; it is not an assertion that the upstream publisher is
error-free.

## Dimension-by-dimension review

### Identity and source admission

The vertical slice binds the observations to source id `bls` and endpoint id
`bls-cpi-v2`. The source record identifies the U.S. Bureau of Labor Statistics
and the official BLS API. The adapter admits only the two explicitly mapped
CPI series (`CUUR0000SA0` and `CUSR0000SA0`). Unknown series are quarantined,
which prevents an aggregator or an accidental series from being silently
promoted to authoritative data.

### Grain and duplicates

The canonical logical grain is `(source_id, series_id, reference_period)`;
the parser's in-memory duplicate key is `(series_id, reference_period)` within
one capture. The SQL schema adds a uniqueness constraint on source, series,
period, and dimensions. A repeated key in one response is quarantined with
`duplicate_logical_key`; the repository test also verifies that inserting the
same canonical observation twice fails.

The current slice does not yet perform a complete cross-capture duplicate and
vintage reconciliation. A later revision may legitimately share a logical
grain, so it must be represented as an observation version rather than
treated as a duplicate row.

### Schema and required fields

The admitted wire grammar is deliberately narrow: `status` must be
`REQUEST_SUCCEEDED`, `Results` must be an object, and `Results.series` must be
a list of objects with `seriesID` and `data`. Each row must provide a valid
year/month shape and a numeric value. Shape drift is a hard failure. The
canonical model requires a bounded id, source, series, period, dimensions,
value, unit, capture, and retrieval timestamps.

### Missingness and numeric validity

The BLS API uses `"-"` for unavailable observations. The adapter records such
rows as quarantine entries, including source footnotes, instead of coercing
them to zero or dropping them. `DataQualityReport` separately counts missing
required fields and non-finite, boolean, or non-numeric values. No implicit
imputation is performed in this phase.

### Temporal semantics

Canonical records distinguish:

`occurred_at` — the CPI reference period represented by the observation;

`effective_at` — when that observation is economically effective;

`published_at` — the official release publication bound;

`available_at` — the later of the documented release bound and the first
observed API time; and

`retrieved_at` — when this capture was retrieved.

The temporal validator rejects naive timestamps and impossible orderings.
The adapter leaves publication/availability unresolved when no release record
is supplied rather than inventing a timestamp. This avoids treating retrieval
time as publication time.

### Revision and conflict behavior

`RevisionStatus` and `ObservationVersion` provide explicit `ORIGINAL`,
`REVISED`, `SUPERSEDED`, and `UNRESOLVED_REVISION` states. `record_revision`
requires an existing prior version and records a supersession relationship;
`record_conflict` retains conflicting values for review. The BLS API response
used here has no vintage identifier, so the vertical slice emits an original
version and documents revision history as unresolved rather than pretending
that the capture is vintage-complete.

### Raw/canonical reconciliation

The raw response is hash-bound and persisted before canonicalization. Replay
uses the exact bytes and parser version. The fixture test accounts for all
source rows: admitted observations plus quarantined rows equal the input row
count, and the payload hash is stable. The repository writes the raw artifact
and its artifact/capture rows as one rollback-safe unit, then stores the hash
beside the capture metadata; duplicate-capture tests verify that failed links
leave neither an orphan row nor an orphan file.

That reconciliation assertion is bounded to the admitted fixture shape. Unknown
series rows are now emitted as one quarantine record per raw row, so the
fixture's `input_rows == admitted_rows + quarantined_rows` accounting includes
those rows. Broader provider coverage still requires provider-specific grain,
vintage, and continuity checks.

## Persistence and query checks

The migration defines source, endpoint, release, artifact, capture,
observation/version, event, evidence, claim, concept, hypothesis, explanation,
learning-reference, and conflict tables. Foreign keys, check constraints,
unique keys, and temporal/search indexes are present. The disposable
PostgreSQL script applies the migration to `postgres:16-alpine` and verifies
the key tables, constraints, and indexes. SQLite tests exercise the same
contract for fast deterministic development; they are not a substitute for
the PostgreSQL run.

The migration declares foreign keys for both sides of the event-evidence join,
and the repository test verifies that a failed link rolls back atomically.

## Evidence inventory

* `fixtures/p6_5/bls_cpi_2024_2025.json` — deterministic captured-style BLS
  response, including valid rows and a missing-value quarantine case.
* `tests/p6_5/test_bls_adapter.py` — replay, payload hash, shape drift,
  source failure, quarantine, and request-bound tests.
* `tests/p6_5/test_admission_temporal.py` — admission immutability, temporal
  ordering, revision, and source conflict tests.
* `tests/p6_5/test_repository.py` — foreign keys, raw artifact persistence,
  duplicate grain rejection, parameterized lookup, and Show Evidence.
* `tests/p6_5/test_security_quality_evaluation.py` — quality-report coverage
  for required fields, grain duplicates, and pass/fail behavior.
* `scripts/verify_p6_5_postgres.sh` — disposable PostgreSQL schema gate.

## Findings and remaining limits

| ID | Severity | Finding | Disposition |
| --- | --- | --- | --- |
| DQ-01 | Medium | BLS API responses do not expose a vintage identifier in this adapter. | Explicitly bounded as `UNRESOLVED_REVISION`; do not claim complete revision history. |
| DQ-02 | Medium | Cross-capture revision reconciliation and source conflict workflows are modeled but not a full ingestion service. | Keep as a P7/production follow-up; preserve every raw capture. |
| DQ-03 | Closed | Event-evidence link lacked a database foreign key. | Closed by the reviewed migration and disposable PostgreSQL gate. |
| DQ-04 | Low | No independent second-source reconciliation or automated release-schedule fetch is included. | Acceptable for the first authoritative-source slice; disclose in product output. |
| DQ-05 | Low | Fixture coverage is narrow and does not establish continuity, range, or seasonal-adjustment correctness for all periods. | Add provider-specific checks before expanding the admitted series set. |
| DQ-06 | Closed | Unknown-series quarantine was series-level, which could hide raw-row counts. | Each unknown-series row is now quarantined separately and included in reconciliation. |
| DQ-07 | Closed | Capture timestamps were previously only non-empty text. | `TransportCapture` now requires timezone-aware order (`first_observed_at <= retrieved_at`). |

## Review conclusion

The deterministic BLS fixture path satisfies the current data-quality contract:
identity and grain are explicit, malformed values fail or enter quarantine,
duplicates and missingness are visible, temporal fields are separated, raw and
canonical fingerprints can be reconciled, and revision uncertainty is not
hidden. The result is **validated for the bounded P6.5 slice**, with DQ-01 to
DQ-05 retained as limitations rather than silently treated as complete source
quality.
