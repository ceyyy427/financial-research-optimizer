# Finathink P8.2 vectorbt Sandbox

**Status:** Finathink-native sweep implemented; isolated vectorbt smoke passed;
core admission deferred
**Date:** 2026-10-03 (Asia/Shanghai)

## Admission posture

vectorbt is classified **C — optional research sandbox**. The audited upstream
release is `1.1.1` (Python `>=3.11,<3.15`) with Apache-2.0 plus Commons
Clause; optional extras may carry additional terms. It is not a standard
permissive core dependency for an open/hosted Finathink product. Legal and
distribution review is required before bundling or hosting it.

vectorbt is absent from the local core and quant environments. An isolated
`.venv-vectorbt` now exists on Python 3.13.7 with vectorbt 1.1.1 and its
reviewed core dependencies; no raw `Portfolio` object enters Finathink core.

## Finathink-owned sweep contract

The first slice uses `run_parameter_sweep()` in
`src/finahinking/p8_2/sweeps.py`. It accepts a bounded
`ParameterSweepSpecification`, enumerates declared combinations in deterministic
order, evaluates every cell, and returns a `SweepResult` containing:

- all experiments, including structured cell failures/pending values;
- train, validation, and OOS values;
- experiment count and selection policy;
- multiple-testing warning and adjustment status;
- robust and unstable regions;
- OOS comparison records and a deterministic fingerprint.

The implementation intentionally does not emit a `BEST STRATEGY` label. A
vectorbt adapter, if later admitted, must produce the same normalized result;
`vectorbt.Portfolio` remains a private provider object.

## Proposed adapter topology

```text
Finathink ParameterSweepSpecification
             │ explicit grid/splits/costs
             ▼
       vectorbt adapter (future)
             │ private `.venv-vectorbt`
             ▼
Finathink SweepResult + warnings + fingerprints
             │
             ▼
Parameter Lab / chart/table / learning trace
```

The adapter must preserve transaction costs, slippage, benchmark, rebalance
conventions, PIT/OOS boundaries, dataset lineage, and every experiment. It may
accelerate calculations but cannot mine silently, decide a release, or infer
investment advice.

## Isolation and license gate

A future spike must:

1. create a dedicated `.venv-vectorbt` without changing `.venv`,
   `.venv-quant`, or `requirements.lock`;
2. pin vectorbt `1.1.1` (or a separately reviewed version) and capture Python,
   platform, `pip freeze`, `pip check`, and license notices;
3. use a small offline fixture and no `full`/`all` extras by default;
4. run a deterministic grid/sensitivity smoke with OOS and multiple-testing
   metadata;
5. normalize output and test that no raw provider class reaches core/UI;
6. obtain legal review for Commons Clause and any extra/provider licenses;
7. rerun core tests with vectorbt absent.

The upstream dependency surface includes recent NumPy/pandas, SciPy, Numba,
Matplotlib/Plotly, scikit-learn, and optional external data/API packages.
Metadata compatibility with the local Python 3.13.7 is not integration proof.

## UI semantics

The Parameter Lab shows an experiment ledger, OOS values, robustness/instability
regions, and warnings. It uses the current six-cell deterministic fixture
sweep for an offline demonstration and labels it `SAMPLE`. A heatmap or line
chart must retain the experiment count, split context, and limitations; no
single cell is visually or textually promoted to a winner.

## Evidence status

The internal sweep tests pass in the focused P8.2 suite, including deterministic
ordering, OOS values, multiple-testing warning, and absence of “best strategy”
language. The isolated `scripts/p8_2_vectorbt_smoke.py` also passed with
vectorbt 1.1.1 (six fixture rows, `raw_objects_returned: false`, and
`pip check` reported no broken requirements). This is an offline smoke, not an
adapter admission or license clearance: Commons Clause redistribution terms,
Finathink adapter normalization, and scale/performance evidence remain open.
The Finathink-native engine is still the required core fallback.
