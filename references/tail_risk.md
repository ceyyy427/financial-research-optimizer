# Tail risk, distribution sensitivity and effective subsets

## Tail variance contract

Let (L_w=-w^	op r) be the portfolio loss and let (q_alpha) be its
(alpha)-quantile. The empirical tail set is

\[
\mathcal T_\alpha=\{L_t:L_t\ge q_\alpha\}.
\]

The three reported quantities are

\[
\operatorname{VaR}_\alpha(L)=q_\alpha,
\qquad
\operatorname{CVaR}_\alpha(L)=E[L\mid L\ge q_\alpha],
\]

\[
\operatorname{TV}_\alpha(L)=operatorname{Var}(L\mid L\ge q_\alpha).
\]

For a finite sample with (m=|\mathcal T_\alpha|\),

\[
\widehat{\operatorname{TV}}_\alpha
=\frac{1}{m-1}\sum_{L_t\in\mathcal T_\alpha}
(L_t-\overline L_\mathcal T)^2,
\quad m>1.
\]

When (m\le1), the estimator is reported as zero with a warning; the result
must not be interpreted as evidence that the tail is stable. The core runtime
uses a moving-block bootstrap because financial losses are serially dependent.
Each draw samples overlapping blocks of length (b), preserves the original
sample length, and recomputes all three quantities. The seed, (b), and number
of replications are part of the experiment lineage.

## Distribution registry

`empirical` and `gaussian` are implemented by the dependency-light core. The
registry also admits `student_t`, `generalized_laplace`, and
`elliptical_mixture`; they remain explicit `not_available` challengers until a
declared likelihood, parameter fit, PIT diagnostic and failure test is enabled.
This prevents a Gaussian approximation from being mislabeled as a heavy-tail
fit. Any parametric candidate must disclose its parameter estimator, tail
calculation, PIT/QQ diagnostic, and short-sample boundary.

## Effective asset subset test

For base returns (R_B) and candidate returns (R_C), test

\[
H_0:\quad C \text{ does not expand the mean--variance opportunity set of } B.
\]

The shipped screening statistic is the increase in the best single-series
Sharpe ratio after adding (C), with the candidate residualized on the base
span under the null. It is intentionally labeled a screening statistic rather
than a full Huberman--Kandel implementation. Its p-value is obtained from a
moving-block bootstrap that preserves serial dependence. Candidate family,
block length, repetitions, seed, short-sale rule and rolling windows must be
pre-registered. A rejection means `candidate_non_redundant_under_protocol`, not
that the asset will earn a future return.

## High-dimensional selector boundary

When (p\gg n), use a train-window-only Fisher separation score, elastic net,
PCA or sparse factor challenger before covariance estimation. Selection
stability, regime frequency, purge/embargo and sample-out-of-sample impact are
required. A selected factor is not allowed to enter a later window if its
selection used that window's label.
