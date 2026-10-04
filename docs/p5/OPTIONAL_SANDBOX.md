# P5 Optional Adapter Sandbox

## Admission decision

`statsmodels` is the first B-class optional adapter admitted to an isolated
sandbox. It is not a Finahinking core dependency and no external model object
crosses the adapter boundary. The sandbox is ignored by Git at `.venv-quant/`.

## Installation evidence

- Environment: CPython 3.13.7, macOS arm64 (`arm64`)
- Package: `statsmodels==0.15.0`
- License: BSD-3-Clause
- Wheel selected: `cp313` / `macosx_11_0_arm64`
- Direct dependency tree: `formulaic==1.2.2`, `numpy==2.5.3`,
  `packaging==26.3`, `pandas==3.0.6`, `patsy==1.0.3`, `scipy==1.18.1`
- Transitive packages: `interface_meta==2.0.1`, `narwhals==2.26.0`,
  `python-dateutil==2.9.0.post0`, `six==1.17.0`,
  `typing_extensions==4.16.0`, `wrapt==2.5.0`
- Test tooling added only to the sandbox: `pytest==9.1.1`,
  `iniconfig==2.3.0`, `pluggy==1.6.0`, `pygments==2.21.0`
- `pip check`: PASS

## Adapter smoke

The isolated environment ran a deterministic four-row OLS fixture through
`StatsmodelsAdapter.fit_ols`. It returned the Finahinking-owned
`RegressionResult` with normalized parameters (`const ≈ 1`, `x = 2`) and a
stable fingerprint; the result contained no fitted statsmodels model object.
This OLS call is an adapter admission/smoke benchmark, not a user-facing
QuantRun; user-facing experiments enter through `run_quant_experiment` (or a
future typed wrapper that creates the same ResearchRun/Artifact chain).
The full project suite was also run against this environment with
`PYTHONPATH=src .venv-quant/bin/pytest -q -rs`: **74 passed, 1 skipped**. The
single skip is the expected main-environment absence test because statsmodels
is intentionally present in this approved sandbox.

The main `.venv` and project dependency manifest were not modified. All other
P5 candidates remain uninstalled pending a separate user-selected admission,
benchmark, and license/security review.
