# Finathink P8.2 Qlib Adapter

**Status:** typed fallback seam implemented; isolated Qlib 0.9.7 model smoke
passed; provider/native admission deferred
**Date:** 2026-10-03 (Asia/Shanghai)

## Admission posture

Qlib is classified **C — optional research sandbox**. It may provide dataset
handlers, feature preparation, model training, LightGBM workflows, and
evaluation examples, but it cannot own Finathink's domain contracts,
provenance, PIT/OOS policy, or UI vocabulary.

The audited reference record identifies Qlib upstream commit
`be725493eb1a6bbb42bf11b37aa7669f59610ff1`, published `pyqlib` 0.9.7,
MIT license, and Python classifiers through 3.12. The core interpreters are
Python 3.13.7 and keep Qlib absent; an isolated macOS arm64 Python 3.12.15
environment (cross-checked
under Linux/amd64 Docker) imported Qlib 0.9.7 and ran an in-memory LightGBM
train/validation/OOS path, but no provider was initialized and no external
dataset was downloaded. No production Qlib result is claimed.

## Adapter boundary

```text
Finathink DatasetSnapshot + MLResearchSpecification
                 │ validated fingerprints/scopes
                 ▼
          QlibResearchAdapter
                 │ private Qlib process/environment (future)
                 ▼
Finathink MLResearchResult + artifact/provenance/limitations
```

The current `QlibResearchAdapter` checks Finathink-owned types and runs a
transparent deterministic baseline. When Qlib is absent (or the adapter is
forced unavailable), it returns status `NOT INSTALLED`, engine
`finathink-deterministic-baseline`, normalized metrics/predictions, and an
explicit fallback limitation. If a package happens to be importable before an
isolated smoke gate is admitted, the adapter still retains the baseline and
reports `FALLBACK`; availability alone is not admission.

Raw Qlib handlers, datasets, models, workflow objects, MLflow records, and
result classes must never be serialized, persisted in `ResearchRun`, or sent
to the frontend. The return record carries only model identity/configuration,
feature and dataset fingerprints, train/validation/OOS scopes, metrics,
predictions/artifact fingerprints, environment metadata, warnings, and
limitations.

## Research protocol

The Finathink-owned ML sequence is:

```text
Question → Dataset → Features → Target → Split → Model
       → Train → Validate → OOS → Explain → Learn
```

An adapter must receive an explicit as-of policy, approved dataset/feature
fingerprints, resource limits, and model allow-list. It must reject a
dataset-fingerprint mismatch, invalid/non-finite values, missing split scope,
or user-supplied executable configuration before invoking Qlib.

The deterministic fallback currently uses a mean-close baseline over the
fixture and labels its metrics as descriptive. Production research must not
reuse this baseline as evidence of predictive performance without reviewing
target construction and leakage.

## Isolation and installation plan

Do not install Qlib into `.venv` or `.venv-quant`. A future spike requires a
dedicated `.venv-qlib-py312` (or equivalent), pinned release/commit, a small
licensed fixture dataset, and captured environment metadata:

1. verify Python 3.12 and native prerequisites (including possible macOS
   OpenMP/LightGBM requirements);
2. install the exact reviewed Qlib distribution and record `pip freeze`,
   `pip check`, license notices, and source hashes;
3. initialize Qlib against the fixture without downloading unreviewed market
   data;
4. run one LightGBM train/validation/OOS smoke workflow;
5. normalize the result and prove no Qlib object leaks;
6. run core tests with the sandbox absent and record retention/removal choice.

Qlib's broad dependency surface (MLflow, Redis, LightGBM, CVXPY, Jupyter,
PyArrow, and others) is materially larger than Finathink core. This is why the
adapter and environment remain optional.

## Data-quality and security gates

- Dataset availability and feature timestamps must satisfy PIT rules before
  training.
- Train/validation/OOS periods, target construction, and revision policy are
  explicit in the normalized result.
- Model/code configuration is allow-listed; no `eval`, `exec`, subprocess,
  network callback, credential, or arbitrary import path is accepted.
- Artifacts include dataset, feature, split, code, model, and environment
  fingerprints plus uncertainty/limitations.
- Missing Qlib is a visible capability state, never an application startup
  exception.

## Evidence status

The current adapter and fallback tests pass in the focused P8.2 suite. The
isolated Docker smoke passed for Qlib import/version and in-memory LightGBM
OOS training (`qlib 0.9.7`, `lightgbm 4.7.0`, four train rows, two test rows),
with `raw_objects_returned=false`. A dedicated native Python 3.12 environment,
Qlib provider initialization/PIT dataset, MLflow integration, model
reproducibility, and an external-license/terms review remain **NOT VERIFIED**.
Qlib remains a replaceable teaching/research provider, not a release
prerequisite.
