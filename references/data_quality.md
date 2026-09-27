# Data quality and schema drift

`validate_financial_dataset.py` treats a row as an observation, not merely a CSV line. The inferred grain is `instrument × observation timestamp × field × vintage`; any available subset is reported, and a missing dimension is visible rather than assumed safe.

The quality report contains:

- `grain`: duplicate grain rows, mixed vintage groups and mixed unit groups;
- `quality`: completeness, freshness, point-in-time, source reliability, date and grain scores;
- `decision`: `usable`, `usable_with_warning`, `degraded` or `blocked`.

The score is deterministic and recomputable from the snapshot. Invalid dates, failed point-in-time checks, or duplicate grain are hard stops. `scripts/schema_drift.py` compares a reference/current CSV or JSON Schema and reports new fields, missing fields, changed types and changed units. A drift report must be added to provenance and reviewed before refreshing model inputs.

```bash
python3 scripts/validate_financial_dataset.py tests/fixtures/synthetic_financial.csv --output artifacts/data_quality.json
python3 scripts/schema_drift.py reference.csv current.csv --output artifacts/schema_drift.json
```
