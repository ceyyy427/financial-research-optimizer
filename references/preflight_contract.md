# Preflight contract

`run_preflight.py` is the blocking gate before feature construction, model fitting, or portfolio optimization. It consumes the same `research_config.json` as every downstream stage and optionally checks the experiment Manifest, analysis JSON, dataset path, source reconciliation result, freshness result, and monitoring result. When an analysis JSON is supplied, its result lineage is verified before the run can be ready.

## Output levels

| Level | Required checks | Reader-facing output |
|---|---|---|
| `minimal` | Config, source identity, basic dates | compact HTML and decision table |
| `standard` | Minimal plus point-in-time and feature/label checks | standard modules, forecast evidence, model card |
| `research_grade` | Standard plus Manifest, rolling evaluation, calibration, applicable overfitting tests | full audit HTML, decision table, reproducibility fields |
| `portfolio_grade` | Research grade plus dataset, reconciliation, covariance robustness, constraints and fallback | full portfolio attribution and binding-constraint output |

The preflight result is `ready` only when no required check is missing or failed. A source conflict, future availability timestamp, label leakage, unmatched config/Manifest fingerprint, or missing required artifact produces `blocked`; no dependent prediction or allocation may be presented as selected.

Dynamic online status is `ready`, `stale`, `degraded`, `fallback`, or `blocked`. Only `blocked` exits with a blocking status; all non-ready states must remain visible in HTML and decision rows.

```bash
python3 scripts/run_preflight.py \
  --config examples/research_config.json \
  --manifest examples/experiment_manifest.json \
  --analysis examples/demo_analysis.json \
  --output artifacts/preflight.json
```
