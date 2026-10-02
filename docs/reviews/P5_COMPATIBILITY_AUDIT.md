# P5 Compatibility Audit

> **Historical P4 compatibility snapshot (superseded):** The implementation
> prohibition below applied before P5 approval. Current P5 evidence is in
> `docs/reviews/P5_FINAL_VALIDATION_REPORT.md`.

**Result:** READY FOR HUMAN-APPROVED DESIGN; P5 remains unimplemented

## Can P5 connect to ResearchRun?

Yes. A future P5 can treat Strategy, Portfolio, Position, Order, Trade, Return,
Risk, and Performance Attribution as versioned experiment artifacts. The
ResearchRun remains the envelope for question, hypothesis, datasets, method,
parameters, result, conclusion, insight, limitations, and fingerprints.

The safest integration is additive:

```text
ResearchRun
  -> strategy identity/configuration
  -> portfolio and execution assumptions
  -> order/trade/position ledger fingerprint
  -> return/risk/attribution evidence fingerprint
  -> human conclusion and insight
```

Large ledgers should be referenced by immutable content identifiers rather than
silently embedded without size limits. Any schema extension requires a version
and migration rules for P4 records.

## Can backtest results become Evidence?

Yes, if a result includes the complete data universe, benchmark, calendar,
strategy version, parameters, position/order/trade ledger, transaction costs,
slippage, corporate actions, survivorship policy, return series, risk metrics,
and validation status. A summary performance number alone is not sufficient
evidence.

## Can Evaluation become Insight?

Evaluation can inform an insight, but the two must remain distinct. Metrics and
diagnostics are evidence; conclusion and insight are human-authored
interpretations with uncertainty and limitations. P5 must not turn evaluation
automatically into advice or a profitability claim.

## Architecture that must remain unchanged

- ResearchRun remains the durable research-memory boundary.
- Providers remain isolated network boundaries and tests remain offline by
  default.
- Dataset provenance, canonical serialization, and fingerprints remain
  mandatory.
- Stored artifacts remain data-only; no pickle or stored-code execution.
- Question, hypothesis, conclusion, insight, and limitations remain explicit.
- The no-brokerage, no-automation, and no-investment-advice invariants remain.
- P5 must add research-validity controls instead of weakening P4 validation.

## Missing prerequisites before implementation

- Exact ledger schemas and cash/position invariants.
- Timestamp and same-bar execution policy.
- Costs, slippage, benchmark, calendar, corporate-action, delisting, liquidity,
  capacity, and survivorship rules.
- Training/evaluation separation, walk-forward evidence, uncertainty, and
  multiple-testing policy.
- Approved dependency and license decision.
- Deterministic fixtures, resource limits, migration tests, and independent
  security/research review.

## Decision

P4 is compatible with a future P5 through additive evidence artifacts. P5 may
enter design only after human approval; implementation remains forbidden.
