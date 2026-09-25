# Portfolio covariance and perturbation robustness

Forecast selection and portfolio construction are separate. For the same expected return vector, compare covariance estimators and perturb the inputs before accepting weights.

## Covariance estimators

1. **Sample covariance**
   \[
   \hat\Sigma_S=(T-1)^{-1}\sum_{t=1}^{T}(r_t-\bar r)(r_t-\bar r)^\top.
   \]
   It is transparent but unstable when assets or factors are numerous relative to \(T\), and it can be ill-conditioned.
2. **Ledoit–Wolf shrinkage**
   \[
   \hat\Sigma_{LW}=\rho F+(1-\rho)\hat\Sigma_S,
   \quad 0\le\rho\le1,
   \]
   where \(F\) is a structured target and \(\rho\) is estimated from the data. Record the target and fitted shrinkage intensity.
3. **Factor covariance**
   \[
   r_t=Bf_t+\epsilon_t,\qquad
   \hat\Sigma_F=B\hat\Sigma_fB^\top+\operatorname{diag}(\hat\sigma_\epsilon^2).
   \]
   Estimate factors only with information available in the training window and record factor definitions, loadings version, and residual treatment.
4. **Robust covariance**

   Use a declared robust estimator or robust loss/weighting scheme that limits outlier influence. Record tuning, observations downweighted, positive-semidefinite repair, and the trade-off between contamination protection and regime information.

## Common optimization contract

For each covariance candidate solve the same declared problem:

\[
\max_w \hat\mu^\top w-\frac{\gamma}{2}w^\top\hat\Sigma w
-\kappa\|w-w_{t-1}\|_1,
\]

under the same budget, turnover, drawdown proxy, leverage, liquidity, and CVaR constraints. Record solver status, objective, active constraints, condition number, weights, turnover, and fallback.

## Perturbation grid

Before selection, perturb one input family at a time and jointly: expected returns, covariance, transaction costs, risk aversion, and constraint boundaries. For every scenario output weight intervals, turnover interval, objective change, risk measure, active constraints, solver status, and infeasibility reason. A useful summary is

\[
[\min_s w_{i,s},\max_s w_{i,s}],
\]

over declared scenarios \(s\), not an unreported confidence interval.

## Infeasibility and fallback

If no feasible solution exists, report the first violated constraint and solver status. Use a pre-registered fallback such as prior weights, minimum-risk feasible weights, or cash. Never silently relax max turnover, max drawdown, cost, or leverage limits. The decision table must include the fallback and its trigger.
