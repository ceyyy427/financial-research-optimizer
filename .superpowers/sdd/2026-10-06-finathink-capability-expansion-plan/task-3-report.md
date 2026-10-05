# Task 3 report: governed factor proposal catalog

## Modified files

- `src/finahinking/research/factor_proposals.py`
- `tests/research/test_factor_proposals.py`

The catalog normalizes and validates hypotheses, selects only fixed templates for
mean reversion, momentum, volatility, and liquidity, validates expressions with
the existing factor DSL, enforces the `close`/`volume`/`return_1d` field allow-list,
and produces deterministic proposal IDs. It remains paper-only and does not
write to `FactorRegistry`.

## Verification

TDD RED was confirmed before implementation: test collection failed with
`ModuleNotFoundError: No module named 'finahinking.research.factor_proposals'`.

Targeted tests:

```text
python3 -m pytest -q tests/research/test_factor_proposals.py tests/research/test_factor_loop.py tests/research/test_factor_dsl.py
27 passed in 0.52s
```

Ruff was requested but is unavailable in this environment:

```text
zsh:1: command not found: ruff
```

## Commit

`53e8d2e feat(factors): add governed factor proposal catalog`

## Unverified / concerns

- Ruff linting remains unverified because the executable is not installed.
- No integration changes were made to `FactorResearchRun`; callers can pass the
  resulting DSL proposals through their existing candidate/run path.

## Focused review fixes

- Family-specific signal requirements now reject proposals that cannot produce
  a template (`close` or `return_1d` for price families; `volume` for liquidity).
- Validation now requires the exact governed constraints and recomputes the
  proposal digest from source hypothesis, expression, and required fields.

Regression and existing factor tests after the fix:

```text
python3 -m pytest -q tests/research/test_factor_proposals.py tests/research/test_factor_loop.py tests/research/test_factor_dsl.py
32 passed in 0.66s
```
