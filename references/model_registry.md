# Model registry

`model_registry.md` is the human-readable companion to the model ledger. Every candidate that is fitted, rejected, selected, or used as a benchmark must have one registry entry. This prevents a winning backtest from being detached from its exact architecture and data contract.

## Required fields

| Field | Requirement |
|---|---|
| `model_id` / `version` | stable identifier and immutable version |
| `family` | baseline, regression, time-series, deep, probabilistic, ensemble, optimizer |
| `estimand` | conditional mean, variance, quantile, direction, distribution, utility, etc. |
| `inputs` / `feature_version` | feature IDs, lag window, point-in-time rule |
| `objective` | loss or utility with units and sign convention |
| `parameters` | architecture, hyperparameters, optimizer, regularization |
| `assumptions` | stationarity, dependence, distribution, graph validity, or constraint assumptions |
| `derivation_refs` | sections in `references/model_derivations.md` and related references |
| `training_window` | start/end, rows, cutoff and preprocessing fit scope |
| `validation_protocol` | expanding/rolling method, purge/embargo and selection metric |
| `random_seeds` | every seed used, including bootstrap seeds |
| `overfitting_diagnostics` | DM/WRC/SPA/DSR/PBO results or `not_available` reason |
| `covariance_model` | if portfolio-related: sample, Ledoit-Wolf, factor, robust, or N/A |
| `failure_mode` | known drift, instability, infeasibility, data requirement, or rejection reason |
| `status` | candidate, rejected, selected, challenger, fallback |

## Selection rule

Register all candidates before inspecting the final test result. The selected model must pass data-quality, point-in-time, source-reconciliation, calibration, and overfitting gates, or be explicitly labeled conditional/insufficient. The registry is part of the experiment manifest and should be hashed with the code and configuration.

## Minimal entry

```yaml
model_id: ensemble-v3
version: 2026-09-26.1
family: ensemble
estimand: 20d excess-return distribution
feature_version: features-v3
objective: weighted CRPS plus turnover penalty
parameters:
  members: [arma-garch, lstm, transformer]
  lookback: 60
derivation_refs: [model_derivations.md#neural-sequence-models, model_derivations.md#probabilistic-and-bayesian-models]
training_window: {start: 2018-01-02, end: 2023-12-29, rows: 1510}
validation_protocol: expanding_window_756_126_252
random_seeds: [7, 11, 19]
overfitting_diagnostics: {DM: pass, WRC: pass, SPA: pass, DSR: warning, PBO: warning}
failure_mode: regime drift and covariance error
status: selected
```

