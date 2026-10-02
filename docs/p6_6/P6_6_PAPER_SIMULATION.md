# P6.6 Paper Simulation Contract

`PaperRun` references a frozen StrategyVersion and an approved dataset. A
virtual clock advances through unseen replay observations. Each step records a
`PaperSignal`, `VirtualOrder`, `VirtualFill`, and `VirtualPortfolio` snapshot.

The fill model is deterministic: next eligible price, explicit side, slippage,
fees, quantity, cash, and position constraints. The portfolio reports equity,
realized/unrealized P&L, turnover, exposure, and benchmark. Restarting from the
same snapshot and fixture must reproduce the same fingerprint.

The model has no broker account, credential, real cash, exchange order ID, or
live endpoint field. A paper order is a simulation record only.

The scalar moving-average reference uses `PaperSimulator` directly. The
multi-asset momentum + low-volatility reference remains on the P5.5 panel
ledger for historical validation; the lab never coerces that panel into a
scalar paper position. Its learning/export path records this boundary as a
limitation until a dedicated multi-asset virtual portfolio contract is
approved.
