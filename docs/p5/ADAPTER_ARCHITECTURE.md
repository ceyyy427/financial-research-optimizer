# P5 Adapter Architecture

The Finahinking domain owns the contracts in `quant/interfaces.py`, the
in-house ledger, evaluation metrics, `Artifact`, and `QuantRun`. Optional
third-party libraries are loaded only from `quant/adapters/` and are converted
immediately into plain Finahinking-owned data.

```text
ResearchRun / Dataset
        |
        v
Finahinking service contract
        |
        v
quant/adapters/<package>  -- lazy import, version/license gate
        |
        v
normalized parameters + metrics + fingerprint
```

`StatsmodelsAdapter.fit_ols` is the first seam. It returns a small
`RegressionResult` containing parameter and metric dictionaries; it never
returns a fitted statsmodels object, stores source code, fetches data, or
changes the core dependency manifest. The adapter was smoke-tested against
`statsmodels==0.15.0` in `.venv-quant`; when the package is absent from an
environment it raises `OptionalDependencyError` with the isolated-install
policy.

The same shape applies to future PyPortfolioOpt, QuantStats/Pyfolio, Alphalens,
bt, vectorbt, Riskfolio-Lib, and TA-Lib adapters. Each must have a component
matrix entry, an exact version and dependency tree, an isolated benchmark, a
license decision, and a removal path before installation.
