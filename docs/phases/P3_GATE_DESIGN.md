# P3 Gate Design — Quant Research Engine

## Success criteria

- User can compute returns, volatility, momentum, drawdown, and correlation.
- User can create a documented factor and evaluate coverage and information coefficient.
- Factor limitations explicitly warn about look-ahead, leakage, costs, and survivorship bias.

## Architecture requirements

- Feature functions are pure and independent of network providers.
- Factor definitions expose name, definition, explanation, limitations, and compute callable.

## Security requirements

- No trading, brokerage, or investment-advice behavior.
- Inputs are validated and numerical failures are explicit.

## Testing requirements

- Deterministic unit tests cover normal, empty, constant, and insufficient-history cases.
- Full suite runs without network access.

## Documentation requirements

- Each shipped factor has an explanation and limitations in code and user documentation.

## Limitations

- No backtest engine, transaction-cost model, optimizer, or ResearchRun persistence.
