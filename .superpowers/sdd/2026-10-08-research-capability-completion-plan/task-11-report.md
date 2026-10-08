# Task 11 report

Implemented deterministic constrained long-only paper portfolio optimization and rebalance recording.

- Added `PortfolioManager.optimize(candidates, risk_result, constraints)` with risk-gate enforcement, single-name and total exposure caps, cash minimums, industry caps, factor bounds, turnover limits, and transaction-cost limits.
- Candidate ordering and allocation repair are deterministic. Infeasible constraints and malformed inputs return a `BLOCKED` proposal with empty weights; the optimizer never falls back to an unconstrained allocation.
- Added `PaperTrader.rebalance(proposal, snapshot)`, which uses the execution policy frozen in the proposal and returns an append-only `PaperLedger` bound to snapshot, proposal, and policy fingerprints.
- Preserved paper-only and secret-safe input boundaries and existing `simulate` behavior.

Red/green evidence: `tests/research/test_portfolio_optimizer.py` initially failed with four missing-interface failures, then passed after implementation.

Validation: focused portfolio/paper/risk suites → 36 passed. Full suite: `python3 -m pytest -q` → 887 passed, 1 skipped, 1 existing multiprocessing fork deprecation warning.

Known limitation: this remains an offline deterministic paper allocator; it does not certify live data, broker behavior, execution, or production deployment.

Fix round 1 addressed review findings: `optimize` now cross-checks passed risk results against PIT, concentration, drawdown, liquidity, and declared limits; unsafe free-form execution-policy keys and values are rejected recursively; proposal constraints and ledger policies are deeply immutable; and negative previous weights fail closed instead of being clamped. Focused regression coverage is 40 passed. Final full-suite validation after the fix is `891 passed, 1 skipped, 1` existing multiprocessing fork deprecation warning.
