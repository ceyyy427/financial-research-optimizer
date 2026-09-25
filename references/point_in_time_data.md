# Point-in-time data and release-timestamp audit

Financial research must model when information became knowable, not only the period to which it refers. Every observation used by a feature or label should carry the following fields.

| Field | Meaning | Typical example |
|---|---|---|
| `observation_date` | period or market date the value describes | CPI reference month; trading date |
| `release_date` | date the publisher released the document/series update | statistical bulletin publication date |
| `availability_date` | first date/time the research pipeline is allowed to use the value | next market session after release |
| `vintage_date` | date/version at which a historical series snapshot was retrieved | real-time vintage or database revision date |
| `effective_timestamp` | timezone-aware timestamp used by the feature join | release time converted to market timezone |

Keep `observation_date` separate from `effective_timestamp`. A quarterly GDP value can describe an earlier quarter but only enter a feature after its release and availability rules. `vintage_date` tracks later revisions and must not overwrite the value available at the forecast origin.

## Required audit rules

### Macro revisions

1. Prefer real-time vintage data with `vintage_date` or `realtime_start/realtime_end` fields.
2. For each forecast origin (t), join the latest vintage satisfying `effective_timestamp <= t`, not the latest revised history.
3. Flag a feature if `vintage_date > t`, `release_date > t`, or the source cannot supply vintage history.
4. If a revised-only series is used for a historical backtest, label the result `revision-biased` and stop dependent claims unless the user explicitly accepts the limitation.

### Financial statement releases

1. Use filing/announcement timestamp, not fiscal period end, as the information time.
2. Enforce `effective_timestamp <= forecast_origin` for every ratio or accounting feature.
3. Keep restatements as new vintages; never silently replace the original filing.
4. For after-hours releases, apply a declared next-session availability rule.

### Historical constituents and survivorship

1. Store membership with `effective_timestamp`, `source_id`, and start/end validity.
2. Reconstruct the universe as known at each historical origin; do not use today's constituent list for the past.
3. Flag delisted, merged, suspended, and removed assets rather than dropping them silently.
4. Include dead and inactive constituents in the evaluation universe when the research question is historical portfolio performance.

## Feature audit output

For every feature store `feature_id`, source IDs, formula/version, `observation_date`, `effective_timestamp`, `vintage_date`, forecast origin, and a boolean `point_in_time_safe`. The feature audit must report counts of future-release rows, revised-vintage rows, invalid constituent joins, and unresolved timestamps. Any nonzero hard violation blocks model selection.

