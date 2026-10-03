# Qlib Reference and Installation Risk (P8.2 Stage A)

Status: read-only upstream/package audit. Qlib was **not installed** into the
main Finathink environment or `.venv-quant`; no training smoke test was claimed.

Audit date: 2026-10-03 (Asia/Shanghai).

## Upstream identity and current status

| Field | Evidence observed |
| --- | --- |
| Repository | <https://github.com/microsoft/qlib> |
| Classification | **C — optional research sandbox**, behind a Finathink adapter |
| Default branch | `main` |
| Latest inspected commit | `be725493eb1a6bbb42bf11b37aa7669f59610ff1` (`ci: pin GitHub Actions to full-length commit SHAs (#2318)`) |
| Latest published GitHub release | `v0.9.7`, 2025-08-15 |
| Latest upstream push observed | 2026-09-22 (GitHub repository metadata) |
| PyPI distribution | `pyqlib` 0.9.7 (PyPI JSON) |
| License | MIT in upstream `LICENSE` and `pyproject.toml` |
| Python metadata | `requires-python >=3.8`; classifiers currently list 3.8–3.12 |
| Local availability | `qlib`/`pyqlib` absent from `python3`, `.venv`, and `.venv-quant` |

The repository is public and active, but its published release and its moving
`main` branch are different snapshots. Pin a commit/release in any future
research environment; do not treat “latest” as reproducible.

Official references: [Qlib repository](https://github.com/microsoft/qlib),
[upstream pyproject](https://github.com/microsoft/qlib/blob/main/pyproject.toml),
[upstream license](https://github.com/microsoft/qlib/blob/main/LICENSE),
[installation/quick start](https://github.com/microsoft/qlib#quick-start), and
[initialization guide](https://github.com/microsoft/qlib/blob/main/docs/start/initialization.rst).

The status table was obtained read-only with `gh api repos/microsoft/qlib`,
`gh api repos/microsoft/qlib/releases/latest`, the upstream `pyproject.toml`
content endpoint, and `https://pypi.org/pypi/pyqlib/json`; no checkout or
package installation was needed for these facts.

## What Qlib is useful for

The upstream project provides a quantitative-research platform with dataset
handlers, feature/data preparation, model training, workflow automation, and
backtest/evaluation examples. The project exposes a `qrun` entry point and
documents a LightGBM workflow. These are candidate capabilities for a bounded
ML research sandbox, not replacements for Finathink's domain contracts.

Qlib must not own or replace:

- `ResearchRun`, `QuantRun`, `FeatureDefinition`, or `StrategySpec`;
- Finathink provenance, dataset fingerprints, point-in-time policy, or OOS
  validity metadata;
- Finathink's backtest engine, paper-only boundary, or UI status vocabulary.

## Dependency and platform risk

The current upstream `pyproject.toml` declares a broad dependency surface,
including NumPy, pandas, `mlflow<3.13`, Redis, `dill`, `fire`, `ruamel.yaml`,
`python-redis-lock`, `tqdm`, `pymongo`, `loguru`, LightGBM, Gym, CVXPY,
joblib, Matplotlib, Jupyter, nbconvert, PyArrow, pydantic-settings, and
`setuptools-scm`. Optional groups add RL (`torch`, `numpy<2.0`), analysis
(`plotly<7`, statsmodels), clients, docs, and test tooling.

This is materially larger than Finathink's core (`numpy`/`pandas` plus optional
Jupyter), so it must not be added to the main environment. The current local
interpreter is Python 3.13.7, while Qlib's current classifiers stop at 3.12;
that is not proof that 3.13 cannot work, but it is an unverified compatibility
boundary. The mission's proposed dedicated Python 3.12 environment is the
conservative choice.

The upstream README specifically warns that non-Conda installs can miss native
headers and that macOS Apple Silicon may need OpenMP (`brew install libomp`)
when building LightGBM. Qlib initialization also requires prepared provider
data (for example a `qlib_data` directory) before a meaningful training run.
Neither native setup nor data download was attempted in this audit.

## Finathink adapter contract (proposed, not implemented here)

The adapter should accept only Finathink-owned, normalized inputs:

- dataset and feature fingerprints;
- explicit train/validation/OOS periods and as-of policy;
- model family/configuration and resource limits;
- source/provenance and environment metadata.

It should return a Finathink-owned `MLResearchResult` containing model identity
and version, feature-set identity, split fingerprints, train/validation/OOS
metrics, prediction artifact fingerprint, warnings/limitations, Qlib version,
and a reproducible environment record. Raw Qlib handlers, datasets, models,
and result objects must not cross the adapter boundary.

## Installation-spike decision

The initial upstream reference audit performed no package installation. The
subsequent isolated spike uses a separate environment and does not alter this
reference record. A future provider-admission spike should:

1. create a dedicated `.venv-qlib-py312` (or equivalent isolated environment);
2. pin the exact `pyqlib` release/commit and capture `pip freeze`/`pip check`;
3. prepare a small, licensed fixture dataset rather than silently downloading
   production data;
4. run one LightGBM training + validation + OOS smoke workflow;
5. normalize the output into a Finathink artifact and prove no Qlib object leaks;
6. delete/retain the sandbox explicitly after the human gate.

Until that provider-admission spike passes, Qlib's status is **candidate /
isolated-smoke-only**, and the core app must continue to work with Qlib absent.

## Follow-up installation evidence

The native macOS host now has Python 3.12.15 in the isolated
`.venv-qlib-py312`; `pyqlib==0.9.7`, `pip check`, and an in-memory Qlib
`LGBModel` LightGBM train/validation/OOS smoke pass. A Linux/amd64 Docker
cross-check produces the same bounded result. Provider initialization, a
licensed PIT fixture, and full normalized adapter integration remain pending
in `QLIB_DEPENDENCY_REVIEW.md`; the core adapter therefore retains the
Finathink deterministic fallback.
