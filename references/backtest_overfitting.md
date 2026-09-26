# Backtest overfitting and data-snooping diagnostics

Backtest performance is a selection problem, not proof of future returns. Run these tests after the rolling forecast ledger exists and before model/portfolio selection is frozen. They complement, rather than replace, time-based validation and economic stress tests.

## Common input contract

Use a timestamp-aligned table with one row per evaluation date and columns for realized target/loss plus each candidate's forecast or strategy return. Record the candidate count, selection rule, number of trials/variants, dependence structure, block length, random seeds, and the exact development/test windows. Use net-of-cost returns for economic tests, but retain gross returns for diagnosis.

## 1. Diebold-Mariano (DM)

### Use and null

Compare two predictive forecasts for the same target and horizon under a declared loss (L). For forecast errors (e_{i,t}=y_t-hat y_{i,t}), define

\[
d_t=L(e_{1,t})-L(e_{2,t}),\qquad H_0:E[d_t]=0.
\]

For multi-step forecasts, (d_t) is serially dependent. Estimate the long-run variance with a HAC estimator, for example

\[
\hat\Omega=\hat\gamma_0+2\sum_{k=1}^{K}w_k\hat\gamma_k,
\quad \hat\gamma_k=T^{-1}\sum_{t=k+1}^{T}(d_t-\bar d)(d_{t-k}-\bar d),
\]

and compute (DM=\bar d/\sqrt{\hat\Omega/T}). A small-sample Harvey–Leybourne–Newbold correction may be reported separately; it does not repair misspecified dependence.

### Input/output

- Input: paired forecasts, realized observations, horizon, loss, HAC bandwidth/kernel, and optional small-sample correction.
- Output: mean loss differential, DM statistic, two-sided or one-sided p-value, confidence interval, effective sample size, and diagnostics for autocorrelation.

### Steps and failure boundaries

1. Align forecast origins and realized outcomes without dropping unequal dates selectively.
2. Compute (d_t) from the pre-registered loss.
3. Select HAC bandwidth from the horizon or a rule fixed before inspection.
4. Report the direction and uncertainty, not only a p-value.

Do not use ordinary iid variance for overlapping horizons. Do not use DM as a many-model search correction, for nested-model comparisons without an appropriate variant, or after selecting the pair on the same test sample.

## 2. White Reality Check (WRC)

### Use and null

Test whether the best observed strategy among (M) candidates outperforms a benchmark after accounting for data snooping. Let (g_{m,t}) be centered performance differences and (T_m=\sqrt{T}\bar g_m). The max statistic is

\[
T_{\max}=\max_{m\le M}T_m.
\]

Generate dependent bootstrap samples (g^*_{m,t}), re-center under the null, and estimate

\[
\hat p_{WRC}=B^{-1}\sum_{b=1}^{B}{\bf1}\{\max_m T^*_{m,b}\ge T_{\max}\}.
\]

### Input/output

- Input: candidate-by-time net performance matrix, benchmark, block/stationary bootstrap, repetitions (B), and random seed.
- Output: observed maximum, bootstrap null distribution, p-value, candidate count, block rule, and the benchmark definition.

### Steps and failure boundaries

Center performance relative to the benchmark, preserve cross-candidate dependence in each bootstrap draw, and disclose the full candidate family. WRC can be conservative and have low power when many poor candidates are included. It is invalid when the candidate family is silently expanded after seeing results or when the bootstrap destroys volatility/regime dependence.

## 3. Superior Predictive Ability (SPA)

### Use and null

SPA tests whether at least one candidate has positive predictive ability relative to a benchmark while controlling for the many-model search. Let (d_{m,t}) be loss or return differences and define the one-sided studentized statistics

\[
Z_m=\frac{\sqrt{T}\bar d_m}{\hat\sigma_m},
\qquad Z_{SPA}=\max_m Z_m^+.
\]

The null is (E[d_m]\le0) for every candidate. Bootstrap the centered, studentized process and compute the probability of exceeding the observed (Z_{SPA}).

### Input/output

- Input: candidate differences, benchmark, studentization rule, bootstrap scheme, trimming/threshold rule, (B), and seed.
- Output: SPA statistic, p-value, per-candidate differences, effective candidate count, and whether a candidate passes the declared threshold.

### Steps and failure boundaries

Use the same candidate family disclosed before testing and preserve serial/cross-sectional dependence. SPA has better power than WRC when many candidates are poor, but it remains sensitive to bootstrap choice, benchmark contamination, short samples, and a candidate family defined after the fact.

## 4. Deflated Sharpe Ratio (DSR)

### Use and null

DSR adjusts a selected Sharpe ratio for non-normal returns, finite samples, and the number of trials. A probabilistic Sharpe ratio relative to threshold (SR^*) can be written as

\[
PSR=\Phi\!\left(
\frac{(\widehat{SR}-SR^*)\sqrt{T-1}}
{\sqrt{1-\hat\gamma_3\widehat{SR}+\frac{\hat\gamma_4-1}{4}\widehat{SR}^2}}
\right),
\]

where (hat\gamma_3) is skewness and (hat\gamma_4) is kurtosis. Set (SR^*) to the expected maximum Sharpe implied by (N) independent/effectively independent trials, for example the Euler-constant approximation

\[
SR^*\approx(1-\gamma)\Phi^{-1}(1-1/N)+\gamma\Phi^{-1}(1-1/(Ne)).
\]

The DSR is (PSR) evaluated at this deflated threshold. State whether (N) is the raw trial count or an effective count adjusted for correlated variants.

### Input/output

- Input: selected strategy returns, sample size, annualization convention, skewness, kurtosis, trial count/effective trial count, and target confidence.
- Output: observed Sharpe, deflated threshold, DSR probability, moments, trial-count assumption, and sensitivity to (N).

### Steps and failure boundaries

Use net returns and the same frequency as the decision ledger. Do not annualize inconsistently, assume Gaussian returns when tails are material, or call a high DSR a guarantee. DSR is not a substitute for a time-series split and can be unstable with very short samples or poorly estimated higher moments.

## 5. Probability of Backtest Overfitting (PBO)

### Use and null

PBO estimates how often the strategy selected in one sample half fails to rank positively in the held-out half. In combinatorial symmetric cross-validation, split (T) observations into (S) groups, create train/test complements, select the best candidate in each train set, and compute its percentile rank (r) in the paired test set. The logit is

\[
\lambda=\log\frac{r}{1-r}.
\]

Estimate

\[
PBO=\Pr(\lambda<0),
\]

the fraction of combinations where the in-sample winner ranks below the median out of sample.

### Input/output

- Input: candidate-by-time returns/losses, number of groups, train selection metric, held-out metric, cost convention, and seed.
- Output: PBO, distribution/quantiles of (lambda), number of combinations, selected candidates, and train/test score gap.

### Steps and failure boundaries

Use only chronologically admissible combinations when the target has overlap or a purge/embargo requirement. PBO is unreliable with too few observations, highly dependent candidates, unstable regime changes, or a selection metric different from the declared research objective. It diagnoses selection instability; it does not estimate a causal probability that a live strategy will lose.

## Applicability and reporting

Evaluate applicability before running a method. Store `applicable`, `applicability_reason`, `status`, and the minimum input requirement for each of DM, WRC, SPA, DSR, and PBO. A method with insufficient candidates, trials, observations, paired losses, portfolio returns, or admissible splits is `not_applicable`, not a failed hard gate. Only applicable methods can set the aggregate gate to `warning` or `failed`. Suggested common gates remain: no unresolved source conflict, no leakage flag, untouched final test, declared candidate family, valid block/purge rule, and reproducibility manifest complete. A conservative decision table row is `wait / insufficient evidence` when an applicable gate fails.
