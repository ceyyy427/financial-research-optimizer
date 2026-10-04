# P7.5 Data → Math → Code → Finance

This is the signature cross-surface contract for the reference curriculum.
Each concept owns links for the financial interpretation, quant application,
and strategy role; the links are typed and inspectable rather than generated
ad hoc by a model.

| Stage | Contract | Example (momentum) |
| --- | --- | --- |
| Data | source, vintage/window, availability, missing-data policy | captured price observations |
| Transformation | exact lag/window and no-look-ahead rule | lag one day, then 20-day compounded return |
| Mathematics | equation and derivation/rule | `M_t = Π(1+r_{t-k}) − 1` |
| Code | bounded example with an input/output contract | `shift(1).rolling(20)` |
| Financial meaning | interpretation with limitations | an empirical recent-performance feature |
| Strategy role | how it enters a declared spec | signal input tested with costs and OOS |

The same contract applies to volatility (rolling feature), beta (regression
exposure), Sharpe and drawdown (evaluation), and backtesting/OOS (research
validity). A code example is not evidence by itself. Quant results must retain
the existing data fingerprint, code commit, split, costs, and provenance.

For real events, P6.5 remains the event source of truth. A CPI event can link
to inflation → rates → bond yields → discount rate → valuation, while the
knowledge record retains the distinction between economic mechanism,
historical association, hypothesis, and direct evidence.
