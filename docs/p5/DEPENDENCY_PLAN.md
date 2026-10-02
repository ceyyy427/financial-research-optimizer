# P5 Dependency Plan

**Status:** No candidate is installed in the project runtime. The approved
statsmodels adapter was installed and smoke-tested only in the isolated
`.venv-quant` sandbox; the core manifest and `.venv` remain unchanged.

## Current environment baseline

The existing project environment is the only runtime used by the P5 gate. It
contains the already-approved NumPy/Pandas project dependencies plus the P1
research tools. The core engine deliberately uses no new dependency. A future
candidate installation must occur in a separate `.venv-quant` environment (or
an equivalent isolated environment), never in the global Python installation.

Before any candidate admission, record:

```text
python --version
pip list
pip check
```

After each individual installation, rerun `pip check`, the existing tests, the
candidate adapter tests, and the deterministic P5 fixture. Record the package
version, license, platform wheel/build result, and full dependency tree.

## Explicit no-blind-install rule

`pip install everything` is prohibited. The following are also prohibited:

- installing into global Python or the frozen project environment without an
  approved matrix entry;
- importing a library directly from a domain module;
- accepting an external library object as a ResearchRun, Artifact, QuantRun,
  Strategy, or EvaluationReport;
- enabling network downloads or optional reporting helpers during tests;
- adding vectorbt, Backtrader, Pyfolio, Ollama, broker SDKs, or live-trading
  packages to the P5 core.

## P5 core decision

The in-house engine is sufficient for the first vertical slice and keeps the
domain contract inspectable. Existing NumPy/Pandas provide the numerical
operations needed for the offline ledger and metrics. The only installed
candidate is the isolated statsmodels adapter sandbox documented in
`docs/p5/OPTIONAL_SANDBOX.md`; no project manifest is changed by this phase.

## Candidate admission order

1. statsmodels for a regression/attribution adapter only if a named P5 use
   case cannot be expressed with current contracts.
2. One reporting adapter, either QuantStats or Pyfolio Reloaded, after a
   fixture comparison; never both as defaults.
3. PyPortfolioOpt or Riskfolio-Lib only after portfolio constraints and solver
   reproducibility are specified.
4. Alphalens Reloaded only after comparing its factor alignment with the P4
   Factor Engine.
5. bt or vectorbt only as optional research adapters after license and
   semantic benchmarks; neither may replace the in-house ledger.
6. TA-Lib only as an optional feature adapter after a macOS arm64 build review.

## Rollback

An adapter is removed by uninstalling only from its isolated environment and
deleting its optional configuration. Core tests must remain green without the
adapter. The Finahinking lock/manifest stays unchanged until a separate
dependency decision is approved.
