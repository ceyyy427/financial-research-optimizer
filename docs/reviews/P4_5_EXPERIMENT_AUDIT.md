# P4.5 Experiment Lifecycle Audit

**Result:** PASS

## Lifecycle mapping

```text
Creation -> Configuration -> Execution -> Validation -> Result Storage -> Insight
```

| Stage | P4 behavior | Evidence |
| --- | --- | --- |
| Creation | User supplies question, hypothesis, dataset, factor, conclusion, and insight. | `ResearchRun.create` and required-field tests. |
| Configuration | Engine records method, horizon, and one-period factor shift. | `ExperimentEngine.execute`; complete-run test. |
| Execution | Factor is computed over validated prices; forward returns and IC/coverage follow. | Engine and factor source/tests. |
| Validation | Horizon, price data, factor alignment, required text, schema, IDs, and fingerprints are checked. | Data, factor, model, engine, and storage failure tests. |
| Result storage | Canonical JSON is written through a path-safe, atomic local store. | `RunStore.save/load`; round-trip and traversal tests. |
| Insight | User-authored conclusion/insight and limitations are stored with evidence. | ResearchRun fields and complete-run test. |

## Deterministic behavior

For identical dataset content, factor metadata/computation, method, and
parameters, the result metrics and fingerprints are deterministic. The default
UUID and creation timestamp are intentionally variable metadata but are not
part of the scientific result fingerprint. Tests and the P4.5 volatility
workflow use explicit IDs/timestamps when complete record equality is required.

## Failure handling and edge cases

- Empty datasets, duplicate dates, missing close columns, nonnumeric/nonpositive
  prices, and unordered dates are rejected.
- Invalid currency syntax and unallowlisted ECB redirects are rejected at the
  provider boundary.
- Nonpositive and boolean horizons are rejected.
- Constant or insufficient factor inputs yield undefined IC rather than a
  fabricated statistic.
- Missing required ResearchRun text, tampered dataset fingerprints, malformed
  JSON/schema, unsafe IDs, and path traversal are rejected.
- An existing run ID cannot be silently replaced with a different record.

The overwrite-conflict branch is implemented but does not yet have a dedicated
test; this is a minor coverage opportunity, not a lifecycle failure.

## Serialization and security

Canonical JSON sorts keys, uses stable separators, normalizes timestamps and
non-finite numbers, and rejects unsupported non-JSON values. Loading verifies
schema version plus dataset and result fingerprints. Storage never deserializes
pickle or executes factor code from a record. The lifecycle evidence includes
the model, engine, storage, and P4.5 workflow tests; the workflow test uses the
checked-in volatility fixture.

## Reproduction

`ExperimentEngine.reproduce` compares dataset fingerprints, checks factor name,
re-executes with recorded horizon, and compares the candidate result
fingerprint. Factor definition or computation changes that alter the canonical
result are detected; implementation identity is not independently hashed.

## Decision

The P4 lifecycle is deterministic for its documented inputs, fail-closed on the
tested invalid cases, serializable, and suitable for local research. **PASS.**
