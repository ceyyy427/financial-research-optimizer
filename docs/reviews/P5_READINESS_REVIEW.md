# P5 Design Readiness Review

**Status:** **READY FOR HUMAN APPROVAL** for design review only

**Implementation status:** P5 is not implemented and no P5 dependency is
installed.

## 1. Backtest architecture requirements

P5 should connect future objects to the P4 ResearchRun as an auditable
extension, not replace it:

| Future object | Role | Required connection to ResearchRun |
| --- | --- | --- |
| **Strategy** | Produces timestamped intents/signals from an information set | Store strategy identity, parameters, and implementation fingerprint as the method configuration. |
| **Portfolio** | Applies sizing, cash, exposure, and account rules | Record the portfolio policy and starting state; never hide them in defaults. |
| **Position** | Current holdings over time | Link each state transition to the ledger and underlying trade. |
| **Trade** | Executed fill or simulated fill | Preserve timestamp, side, quantity, price, fees, slippage, and reason. |
| **Order** | Intent before execution | Separate intent from fill and make execution assumptions explicit. |
| **Return** | Time-indexed portfolio or strategy return | Store the return series fingerprint and its benchmark relationship. |
| **Risk** | Drawdown, volatility, exposure, liquidity, and uncertainty measures | Record definitions, windows, assumptions, and validation status. |
| **Performance Attribution** | Explains where returns came from | Link contributions to positions, trades, factors, and benchmark periods. |

The resulting P5 `ResearchRun` should retain the existing question, hypothesis,
dataset, conclusion, insight, and limitations. Backtest artifacts become
additional evidence attached to the same research record. Strategy output must
be a signal or intent; it must never become an implicit brokerage action.

## 2. Research integrity requirements

Before P5 implementation, the gate must define and test:

- **Transaction costs:** commissions, fees, taxes, and their timing.
- **Slippage:** a deterministic execution model and sensitivity range.
- **Benchmark:** explicit benchmark data, alignment, and missing-data policy.
- **Survivorship bias:** delisted instruments, universe history, and selection
  dates.
- **Look-ahead bias:** the information set available at each timestamp and
  same-bar execution rules.
- **Data leakage:** training, calibration, and evaluation boundaries.
- **Corporate actions:** split, dividend, symbol-change, and adjusted-price
  policy.

Additional mandatory controls should cover calendars/time zones, liquidity and
capacity, turnover, out-of-sample or walk-forward evaluation, multiple testing,
uncertainty, and the distinction between historical simulation and live results.

## 3. Tool evaluation

| Tool | Purpose | License / maintenance signal | Architecture fit | Risk and readiness decision |
| --- | --- | --- | --- | --- |
| **vectorbt** | Vectorized backtesting, portfolio analytics, and parameter sweeps. | Upstream documents Apache 2.0 with Commons Clause; active repository and docs should be rechecked at P5 start. | Good fit for fast research experiments and Pandas/NumPy data, but requires an adapter to preserve ResearchRun provenance. | Candidate for a bounded fixture comparison; no install or approval yet. |
| **Backtrader** | Event-oriented strategies, feeds, orders, positions, and analyzers. | Upstream repository is GPL-3.0 and its compatibility/maintenance assumptions need review. | Strong event model, but stateful integration and license constraints may conflict with the open research laboratory boundary. | Rejected as the default dependency; reconsider only after explicit legal and architecture approval. |
| **Pyfolio Reloaded** | Portfolio performance and risk reports after a ledger exists. | Apache-2.0 upstream fork with its own dependency and report-maintenance surface. | Useful as an optional analysis layer, not a source of execution semantics or a backtest engine. | Conditional candidate for post-ledger reporting; no install yet. |

Sources to re-check before P5 include the [vectorbt repository](https://github.com/polakowo/vectorbt),
[Backtrader repository](https://github.com/mementum/backtrader), and
[Pyfolio Reloaded repository](https://github.com/stefan-jansen/pyfolio-reloaded).

## 4. Readiness conclusion

The P4 architecture is ready to host a future P5 design because ResearchRun
already provides a stable question-to-result record and the local store can
preserve additional evidence. It is not ready for implementation until a human
approves the P5 gate, research-integrity controls, dependency decision, and a
test-first implementation plan.

**Decision:** P5 is **WAITING FOR HUMAN APPROVAL**. Do not implement it in this
phase.
