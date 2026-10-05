# Strategy research guide

The Strategy Lab preserves the same `StrategySpec` in Guided and Advanced
views. Guided mode explains each field; Advanced mode exposes the same typed
contract. A strategy is a research hypothesis, not a trade instruction.

![Finathink 研究总流程](diagrams/finathink-overview.svg)

## Tutorial 1: understand a real financial event

![事件到证据：从捕获事件进入知识语境](diagrams/event-evidence.svg)

```text
BLS CPI (CAPTURED) → claim/evidence → Inflation concept
→ rates/bonds/discounting context → quant check → saved learning
```

Record the source release, capture hash, publication/retrieval times, and
limitations. Do not replace a captured observation with an unlabelled live
value.

## Tutorial 2: learn quant from data

![量化研究：从问题和数据审计进入实验与验证](diagrams/quant-research.svg)

```text
returns → variance/volatility → covariance/correlation
→ regression/beta → Sharpe and drawdown
```

Explain the data, equation, code, and financial interpretation separately.
Record the sample window, annualization convention, missing-value handling,
and assumptions before interpreting a result.

## Tutorial 3: build a strategy

![策略与风控：从策略想法进入回测、OOS 和决策卡](diagrams/strategy-risk.svg)

```text
idea → FeatureDefinition → math/code → backtest → OOS
→ paper simulation → compare evidence → learning
```

The research ledger must expose timing, availability, costs, split boundaries,
parameter choices, and failure modes. No result may imply guaranteed alpha,
forecasting certainty, or live execution. Keep a research question, hypothesis,
counter-evidence, and next test with every iteration.
