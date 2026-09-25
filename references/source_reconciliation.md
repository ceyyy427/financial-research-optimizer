# Multi-source reconciliation and conflict detection

When more than one source reports the same asset and date, reconcile before feature construction. Do not average conflicting prices or volumes to hide provenance differences.

## Comparison key and fields

Join sources on a canonical key `(instrument_id, observation_date, frequency, timezone)` and compare:

- observation and effective timestamps;
- open, high, low, close and volume;
- adjusted/unadjusted convention and corporate-action treatment;
- exchange calendar, holidays, suspensions and timezone;
- missingness, duplicate rows, revisions and source vintage.

## Tolerance and priority

Define tolerances before looking at the disagreement. A field is within tolerance when

\[
|x_a-x_b|\le\tau_{abs}+\tau_{rel}|x_b|,
\]

with separate rules for price, volume and timestamp. A recommended starting point is `price: abs=1e-8, rel=1e-4`, `volume: abs=1, rel=0.005`, and timestamp tolerance equal to the documented market-session boundary; tune only with source documentation.

Source priority is an ordered, recorded list such as `official_exchange > regulator/provider > documented_api > licensed_database > public_aggregator`. Priority selects a source for downstream use only after the conflict is recorded; it never erases the lower-priority observation.

## Conflict status

Use one of:

- `match`: all required fields and metadata agree within tolerance;
- `minor_difference`: numeric difference within declared operational tolerance or explainable rounding;
- `calendar_mismatch`: dates differ because calendars/timezones/sessions differ;
- `adjustment_mismatch`: adjusted and raw conventions are mixed;
- `timestamp_conflict`: release/effective timestamps cannot be ordered safely;
- `material_conflict`: price/volume differs beyond tolerance or values are irreconcilable;
- `missing_source`: one required source has no observation;
- `unresolved`: conflict remains after documented priority and manual rule.

## Algorithm and stopping rule

1. Normalize identifiers, timezone, units and adjustment labels without changing raw values.
2. Join on the canonical key and compare field by field.
3. Apply the pre-registered tolerance and classify each field.
4. Apply source priority only to choose a canonical value; preserve all raw values and evidence.
5. Write a reconciliation record with source IDs, values, deltas, tolerance, priority, status, and resolution.
6. Propagate material statuses to the provenance manifest, data-quality report, feature audit, model card, HTML, and decision table.

Stop dependent analysis when any required asset/date has `material_conflict`, `timestamp_conflict`, `adjustment_mismatch`, or `unresolved`, unless the user explicitly accepts a documented fallback. A `minor_difference` may proceed only with a sensitivity flag. Never use a favorable source selectively after seeing model results.

## Output record

```json
{
  "instrument_id": "SPY",
  "observation_date": "2026-01-05",
  "fields": {"close": {"source_a": 590.1, "source_b": 590.2, "status": "minor_difference", "delta": 0.1, "tolerance": 0.05901}},
  "source_priority": ["official_exchange", "documented_api", "public_aggregator"],
  "canonical_source": "documented_api",
  "conflict_status": "minor_difference",
  "resolution": "use documented_api; retain both raw values"
}
```

