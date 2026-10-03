# VectorBT Reference and License Boundary (P8.2 Stage A)

Status: read-only upstream/package audit. VectorBT was **not installed** into
the main Finathink environment or `.venv-quant`; no sweep smoke test was
claimed.

Audit date: 2026-10-03 (Asia/Shanghai).

## Upstream identity and current status

| Field | Evidence observed |
| --- | --- |
| Repository | <https://github.com/polakowo/vectorbt> |
| Classification | **C — optional research sandbox** |
| Default branch | `master` |
| Latest inspected commit | `ceffc501f2d37033a79dd86a9f883e69ec6977bd` (docs update, 2026-09-26) |
| Latest published release | `v1.1.1`, 2026-09-26 |
| PyPI distribution | `vectorbt` 1.1.1 |
| Python metadata | `>=3.11,<3.15`; classifiers 3.11–3.14 |
| Local availability | absent from `python3`, `.venv`, and `.venv-quant` |

The official docs describe vectorized Pandas/NumPy backtesting, parameter grids,
portfolio analytics, and interactive exploration. See the [official quick
start](https://github.com/polakowo/vectorbt/blob/master/docs/docs/index.md),
[upstream pyproject](https://github.com/polakowo/vectorbt/blob/master/pyproject.toml),
[upstream license](https://github.com/polakowo/vectorbt/blob/master/LICENSE.md),
and [release v1.1.1](https://github.com/polakowo/vectorbt/releases/tag/v1.1.1).

The status table was obtained read-only with `gh api repos/polakowo/vectorbt`,
`gh api repos/polakowo/vectorbt/releases/latest`, the upstream `pyproject.toml`
and `LICENSE.md` content endpoints, and
`https://pypi.org/pypi/vectorbt/json`; no checkout or package installation was
needed for these facts.

## License and distribution risk

The upstream `LICENSE.md` describes **Apache 2.0 with Commons Clause**. The
Commons Clause excludes the right to sell the software or a product/service
whose value derives entirely or substantially from the software. The README
also warns that optional dependencies may have more restrictive licenses.

This is not a standard permissive Apache-2.0-only dependency for a public SaaS
or hosted product. Treat the license as a material admission gate: obtain legal
review for the intended distribution model, preserve notices, and do not bundle
vectorbt into Finathink's core wheel before approval. This record is not legal
advice.

## Dependency and platform risk

The current upstream core dependencies include NumPy `>=2.4.6`, pandas
`>=3.0.3,<4.0`, SciPy, Matplotlib, Plotly, ipywidgets, anywidget, Numba
`>=0.66`, dill, tqdm, dateparser, imageio, scikit-learn, schedule, requests,
pytz, and mypy-extensions. The `rust` extra adds `vectorbt-rust==1.1.1`.
The `full` extra adds TA-Lib, yfinance, python-binance, ccxt, alpaca-py, Ray,
`ta`, pandas-ta-classic, Telegram, and quantstats.

Finathink's current NumPy 2.5.3 and pandas 3.0.6 satisfy the stated core
version ranges, and Python 3.13.7 satisfies the Python bound, but that is only
metadata compatibility—not a tested integration. The optional extras add native
builds, large dependency graphs, external APIs, and additional license review.
Do not install `full` or `all` merely to prove the core package.

## Finathink sweep boundary (proposed, not implemented here)

VectorBT is suitable for a bounded accelerator for parameter grids, threshold
and window sensitivity, rebalance/cost sweeps, and robustness maps. It must not
select a “best strategy,” mine alpha silently, or decide a release.

Finathink should own a `ParameterSweepSpecification` with strategy version,
parameter ranges, experiment count, train/validation/OOS scope, and selection
policy. The normalized `SweepResult` should contain every experiment, metrics,
warnings, multiple-testing metadata, robustness/instability regions, and OOS
comparison. A raw `vectorbt.Portfolio` must never become a Finathink domain
object; an adapter should convert it into a typed artifact with provenance and
fingerprints.

## Installation-spike decision (Stage A audit snapshot)

At the Stage A audit snapshot, no installation or benchmark had been performed.
The planned spike was to use a
dedicated `.venv-vectorbt`, pin 1.1.1 (or a reviewed newer version), run a tiny
offline fixture sweep, capture `pip check`, record license notices, and verify
that the core Finathink app passes with vectorbt absent. The follow-up evidence
below records what has since been run; admission remains deferred.

## Follow-up local sandbox evidence

After this read-only Stage A record, a separate `.venv-vectorbt` was created
without changing `.venv` or `.venv-quant`. It contains vectorbt 1.1.1 on
Python 3.13.7; `pip check` reports no broken requirements, and
`scripts/p8_2_vectorbt_smoke.py` passed on a six-row offline fixture while
returning only scalar summary values (`raw_objects_returned: false`). This
does not change the admission decision: the adapter has not been wired into
core, Commons Clause/extra-license review remains open, and the in-house sweep
is still the required fallback.
