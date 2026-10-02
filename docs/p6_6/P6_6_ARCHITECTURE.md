# P6.6 Architecture

```text
strategy idea
    ↓ interpreter + user review
StrategySpec → FeatureDefinition/Version → FeatureGraph
    ↓ validator + point-in-time gate
Strategy IR → approved compiler → existing P5/P5.5 execution authority
    ↓ ResearchRun / QuantRun / Artifact / fingerprints
analysis → OOS / walk-forward → frozen StrategyVersion
    ↓ approved data + virtual clock
PaperRun → virtual signals/orders/fills/portfolio
    ↓
backtest-vs-paper + feature drift → learning → safe export
```

## Ownership

| Boundary | P6.6 owner | Reuse | Must not do |
| --- | --- | --- | --- |
| Feature definition/version | `p6_6.features` | existing `features.core` math | hide availability, mutate a version, or fetch data |
| Feature graph | `p6_6.features` | P6.5 fingerprints | execute arbitrary graph code |
| Strategy interpretation | `p6_6.strategy` | P6 text validation | silently change user meaning |
| Strategy IR/compiler | `p6_6.ir` / `p6_6.compiler` | P5 `Strategy` protocol | accept Python, SQL, shell, network, or broker nodes |
| Backtest | `p6_6.backtest` orchestration | P5 `BacktestEngine` for the single-asset moving-average slice; P5.5 multi-asset ledger/adapter for the panel momentum + low-volatility slice | fork an execution engine or claim live validity |
| Paper simulation | `p6_6.paper` | P5 trade/cost semantics | create broker orders or real-money state |
| Education | `p6_6.education` | P6 LearningCard/Store | teach formulas unrelated to the actual strategy |
| Export | `p6_6.export` | P4 atomic artifact conventions | export secrets or executable deployment code |

P6.6 records its own StrategyVersion and FeatureVersions while preserving the
existing P5/P5.5 result and provenance envelopes. P5 `BacktestEngine` remains
the single-asset historical execution authority; the already-validated P5.5
multi-asset ledger remains the panel authority. P6.6 supplies only validated
adapters and orchestration, and never treats an educational code export as an
executable strategy.
