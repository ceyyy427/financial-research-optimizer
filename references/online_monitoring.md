# Online monitoring and validity contract

Online monitoring separates data validity from model validity. `scripts/monitoring/freshness.py` checks snapshot age, expected release windows, stale-cache fallback, duplicate rows, provider changes, and HTTP failures. `scripts/monitoring/model_monitor.py` checks feature PSI, prediction mean shift, residual shift, calibration, cost, turnover, and constraint triggers.

Every status is explicit: `ready`, `stale`, `degraded`, `fallback`, or `blocked`. A warning does not silently trigger retraining. The refresh policy decides when to recompute features, forecast with a frozen model, retrain, or run a full research audit. A model drift trigger may request retraining, but retraining must pass the same preflight, rolling evaluation, applicability-gated overfitting checks, and result-lineage verification as the original run.

The HTML must show `as_of_time`, `data_latency`, `data_status`, `model_status`, `forecast_status`, `source_status`, `cache_status`, `forecast_validity`, and `fallback_used` whenever online status is available.
