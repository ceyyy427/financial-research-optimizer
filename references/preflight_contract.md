# Preflight contract

`run_preflight.py` is the blocking gate before feature construction, model fitting, or portfolio optimization. It consumes the same `research_config.json` as every downstream stage and optionally checks the experiment Manifest, analysis JSON, dataset path, and source reconciliation result.

## Output levels

| Level | Required checks | Reader-facing output |
|---|---|---|
| `minimal` | Config, source identity, basic dates | compact HTML and decision table |
| `standard` | Minimal plus point-in-time and feature/label checks | standard modules, forecast evidence, model card |
| `research_grade` | Standard plus Manifest, rolling evaluation, calibration, applicable overfitting tests | full audit HTML, decision table, reproducibility fields |
| `portfolio_grade` | Research grade plus dataset, reconciliation, covariance robustness, constraints and fallback | full portfolio attribution and binding-constraint output |

The preflight result is `ready` only when no required check is missing or failed. A source conflict, future availability timestamp, label leakage, unmatched config/Manifest fingerprint, or missing required artifact produces `blocked`; no dependent prediction or allocation may be presented as selected.

```bash
python3 scripts/run_preflight.py \
  --config examples/research_config.json \
  --manifest examples/experiment_manifest.json \
  --analysis examples/demo_analysis.json \
  --output artifacts/preflight.json
```
