# P7.5 Learning Paths

Paths are typed `LearningPath` records, not ordered headings in a document.
They can be rendered as browseable curriculum, searched by concept, and
joined to P7 mastery evidence through the existing private graph.

| Path | Sequence | Purpose |
| --- | --- | --- |
| `reference-curriculum` (`REFERENCE`) | Return → Compounding → Variance → Standard Deviation → Volatility → Covariance → Correlation → Regression → Beta → Sharpe → Drawdown → Momentum → Backtesting → OOS → Overfitting | End-to-end reference curriculum |
| `regression-path` (`REGRESSION`) | Return → Variance → Covariance → Correlation → Regression → Beta | Data to factor exposure |
| `quant-research-path` (`QUANT_RESEARCH`) | Return → Momentum → Backtesting → OOS → Overfitting | Hypothesis to honest evaluation |
| `strategy-path` (`STRATEGY`) | Volatility → Momentum → Backtesting → Drawdown → OOS → Overfitting | Feature, signal, path risk, validation |

Every concept page progressively reveals intuition, formal definition,
equation, derivation, code, financial meaning, quant/strategy role, and a
context slot. The context slot is intentionally empty until the caller joins a
private P7 artifact; no private data is placed in the public catalog.
