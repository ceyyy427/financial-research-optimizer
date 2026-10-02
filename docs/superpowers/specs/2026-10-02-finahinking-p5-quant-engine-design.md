# Finathink P5 Quant Engine Foundation Design

**Status:** Approved for implementation from the user-supplied P5 execution brief

**Goal:** Add a research-only, deterministic quant runtime that turns a validated
`Dataset` and an explicit strategy into a cost-aware backtest, evaluation report,
artifact, and `QuantRun` linked to the frozen P4 `ResearchRun` contract.

## Scope and non-goals

P5 includes an in-house historical backtest engine, strategy/portfolio/trade
contracts, performance and risk evaluation, a minimal portfolio allocation
helper, reproducible artifacts, provenance, dependency admission records, and
an offline vertical-slice fixture. It does not include broker APIs, order
routing, live trading, automatic investment advice, opaque prediction models,
or agent-generated third-party calls. P6 is out of scope.

## Architecture

The frozen P4 path remains the outer boundary:

```text
Dataset -> Factor -> Strategy -> Backtest Engine -> Evaluation
        -> Artifact/QuantRun -> ResearchRun -> human Insight
```

`src/finahinking/quant/interfaces.py` owns domain-only dataclasses and
protocols. `engines/` contains the deterministic in-house execution loop.
`evaluation/` contains pure metric calculations. `portfolio/` contains sizing
and ledger helpers. `adapters/` is the only place where optional third-party
packages may be imported. The first admitted runtime path uses only the
existing NumPy/Pandas dependencies; candidate external tools remain documented
and uninstalled until a separate admission decision.

## Domain contracts

### Strategy and intent

`Strategy` is a protocol with `strategy_id`, `version`, and
`generate(dataset: Dataset) -> pd.Series`. The series is a dated target-weight
intent in `[-1, 1]`; it is not an order and cannot call a broker. The engine
shifts intents by one bar before execution, so a signal computed from close at
date `t` can only trade at date `t+1`.

### Backtest configuration and result

`BacktestConfig` requires starting cash, fee basis points, slippage basis points,
calendar frequency, benchmark name, and a negative-cash policy. There are no
hidden cost defaults. `BacktestResult` contains dated equity, returns, weights,
trades, and positions plus the configuration and a deterministic fingerprint.
Trade timestamps are monotonic, quantities/prices are finite, and cash is
conserved by explicit fee and slippage debits.

### Evaluation report

`EvaluationReport` derives total return, annualized return, volatility, Sharpe,
Sortino, maximum drawdown, turnover, total fees, total slippage, and benchmark
return from a `BacktestResult`. Undefined statistics are represented as `None`,
never fabricated numbers. Metrics are descriptive historical evidence and are
not investment advice.

### QuantRun and Artifact

`QuantRun` is additive to P4 and has the brief's fields: `id`,
`research_run_id`, `dataset_version`, `strategy_version`, `engine_version`,
`parameters`, `result_artifact`, `fingerprint`, and `timestamp`. `Artifact` is
data-only, schema-versioned, size-bounded, and stores serialized result payloads
and a content fingerprint. `QuantRun` never stores executable code or external
library objects. The adapter layer creates a P4 `ResearchRun` with the existing
`ResearchRun.create` API; it does not redesign or replace `ResearchRun`.

## Temporal and research validity rules

- Dataset dates must be unique, normalized, and increasing.
- Strategy intents are generated from the full historical frame but are shifted
  one period before execution; same-bar execution is rejected by design.
- The backtest records the evaluation window, benchmark, frequency, cost model,
  slippage, and negative-cash policy in parameters.
- The first vertical slice is descriptive and in-sample. Walk-forward and
  out-of-sample splits are explicit future extension points, not implied claims.
- Corporate actions, delistings, survivorship, liquidity, and capacity are
  represented as limitations until dedicated data contracts exist.

## Dependency admission decision

The P5 core admits no new runtime dependency. A component matrix records
repository, license, maintenance/security observations, compatibility risk,
and classification. Statsmodels, PyPortfolioOpt, Alphalens Reloaded,
Pyfolio Reloaded/QuantStats, bt, vectorbt, Riskfolio-Lib, and TA-Lib are
optional or reference candidates behind adapters. Backtrader is rejected as a
default because of GPL-3.0. No candidate is installed by this implementation.

## Error and security behavior

Validation rejects non-finite prices, duplicate dates, unsafe IDs, invalid
weights, negative costs, malformed artifacts, and impossible ledger states.
Persistence is canonical JSON only; no pickle, dynamic import, source
execution, network fetch, credentials, or broker integration is permitted.

## Verification and gate

The P5 gate requires an offline fixture that runs Dataset -> Factor -> Strategy
-> Backtest -> Evaluation -> Artifact -> ResearchRun twice with identical
fingerprints, explicit costs and no look-ahead, plus unit tests for ledger
arithmetic, risk edge cases, temporal integrity, serialization, and forbidden
scope. The final gate also runs governance validation, the full test suite,
Ruff, notebook execution, `pip check`, and an independent architecture,
security, and research-validity review.
