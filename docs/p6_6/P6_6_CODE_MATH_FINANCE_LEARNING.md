# P6.6 Code, Math, Finance, and Learning Contract

`StrategyLearningTrace` maps each strategy component to four explanations:

| Layer | Example |
| --- | --- |
| Code | `rolling(window=20).std()` computes a rolling standard deviation. |
| Math | The sample standard deviation of observations in the trailing window. |
| Finance | Recent realized variability of the asset. |
| Strategy role | Exclude the high-volatility tail before momentum selection. |

The trace also records the research assumption, input/output examples, and
limitation. Learning cards reuse the actual StrategySpec and FeatureVersions;
they cover lagging, rolling windows, ranking, weights, turnover, costs,
slippage, drawdown, OOS, overfitting, and the distinction between historical
evidence and future returns.
