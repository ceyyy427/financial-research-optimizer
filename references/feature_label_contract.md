# Feature and label contract

Every feature and label declares when it became observable and where it came from. The contract is stored under `research_config.json.feature_label_contract` and validated by `feature_label_audit.py`.

Required fields are `feature_id`/`label_id`, `formula`, `source_ids`, `observation_time`, `availability_time`, `forecast_origin`, `label_horizon`, `purge_required`, `embargo_required`, `point_in_time_safe`, and `lineage`; labels additionally require `label_start`, `label_end`, `overlap_group`, target and horizon. `purge_period` removes training observations whose label interval can cross the next evaluation block; `embargo_period` adds a post-training information buffer. Both are measured in observations/days according to the configured frequency and must be recorded in the rolling split artifact.

The audit has two independent gates:

1. `availability_time <= forecast_origin` for every feature row;
2. no training label interval crosses the evaluation boundary after purge and embargo.

An invalid or absent lineage is an audit failure, not an invitation to infer a source. The HTML and decision table should report the feature version, availability field, purge/embargo values, overlap count, and blocking reason.
