# P5 Gate Design — Backtest and Evaluation Engine

**Status:** Design only; P5 implementation is forbidden until human approval.
**Precondition:** P0–P4 gates PASS and the P4 final review is accepted.

## 1. P5 objective

Extend the research laboratory from descriptive factor experiments to a
reproducible, explicitly non-advisory backtest and evaluation boundary. A P5
run must make assumptions, temporal ordering, costs, risk, and uncertainty
auditable rather than producing an unexplained performance number.

Tentative concepts are `Strategy`, `Portfolio`, `Position`, `Trade`, `Return`,
`Risk`, and `Performance Attribution`. These names are placeholders until the
human-approved design fixes their schemas.

## 2. Required architecture

The P4 boundary remains intact:

`provider -> Dataset/Provenance -> validation -> features/factors -> strategy -> portfolio/positions/trades -> returns/risk/attribution -> ResearchRun`

Required separation:

- a strategy produces timestamped intents/signals, never broker actions;
- a portfolio ledger applies explicit sizing, cash, position, fee, slippage,
  and market-calendar rules;
- the evaluator computes returns, drawdown, volatility, turnover, and risk
  metrics from the ledger;
- the P4 ResearchRun remains the durable record, with a versioned method and
  fingerprints for every input and output;
- no component may execute stored code, call a brokerage, or silently fetch
  data during evaluation.

## 3. Acceptance criteria

A future P5 gate may pass only if all of the following are demonstrated:

- a deterministic fixture produces the same trade ledger, return series, risk
  metrics, and result fingerprint twice;
- strategy, portfolio, position, trade, return, risk, and attribution schemas
  are documented and validated;
- every order intent has a timestamp, side, quantity, price rule, and reason;
- fees, slippage, cash, position limits, and market calendars are explicit
  parameters rather than hidden defaults;
- out-of-sample or walk-forward evaluation is possible and clearly separated
  from in-sample fitting;
- the run explains assumptions, conclusion, insight, limitations, and whether
  any statistic is descriptive or predictive;
- drift detection covers data, strategy implementation, parameters, engine,
  and results;
- no output is framed as investment advice or a guarantee of future returns.

## 4. Testing requirements

- Unit tests for ledger arithmetic, cash conservation, position transitions,
  fees, slippage, corporate-action policy, and metric edge cases.
- Property or invariant tests for no negative cash when prohibited, no position
  without a corresponding trade, monotonic timestamps, and deterministic
  fingerprints.
- Regression fixtures for look-ahead, same-bar execution, missing data,
  duplicate timestamps, delistings, splits, and timezone boundaries.
- Temporal tests proving training data cannot include evaluation-period data.
- Security tests for unsafe identifiers, malformed serialized records, resource
  limits, and no code execution.
- Full offline suite, Ruff, governance validation, notebook execution, and
  dependency integrity before the gate review.

## 5. Security requirements

- Keep provider/network access outside the engine; default tests are offline.
- Never deserialize pickle or execute strategy source from a ResearchRun.
- Treat data, symbols, and user-authored conclusions as untrusted input.
- Use path-safe IDs, atomic writes, bounded input sizes, and explicit overwrite
  rules.
- Do not store credentials, brokerage tokens, or personally identifying data.
- Keep any future broker integration permanently out of this phase.

## 6. Research-validity requirements

- Define the information set available at each timestamp and enforce it.
- Make survivorship, delisting, corporate actions, liquidity, and calendar
  assumptions explicit.
- Separate signal generation, execution model, and evaluation window.
- Include transaction costs, slippage, turnover, and capacity assumptions.
- Report uncertainty and sensitivity; do not treat one backtest as proof.
- Require out-of-sample or walk-forward evidence and document multiple-testing
  controls before drawing conclusions.
- Keep a clear distinction between historical simulation and live performance.

## 7. Possible dependencies

The dependency candidates and trade-offs are recorded in
`P5_DEPENDENCY_PLAN.md`. No candidate is installed by this gate-design task.
The preferred first step is a minimal in-house ledger around existing Pandas
contracts, with an external engine considered only after a fixture-based
comparison.

## 8. Forbidden scope

P5 must not include brokerage connectivity, live trading, order routing,
automated investment decisions, financial advice, secrets management, remote
code execution, opaque model-generated strategies, or a claim of profitability.

## Gate procedure

Before P5 implementation, a human must approve this design, the dependency plan,
and a phase-specific implementation plan. A fresh gate review must then verify
architecture, engineering, security, and research validity independently.
