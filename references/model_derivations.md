# Model derivations and diagnostic contracts

This reference is read when the skill needs to explain or implement a model. It is a compact derivation map; the full mathematical exposition in the user's manuscript may be used as additional context.

## Regression

For y = X beta + epsilon, minimize 1/2 ||y-X beta||^2. The first-order condition is X'X beta = X'y. If rank(X)=p, the objective is strictly convex and beta_hat=(X'X)^(-1)X'y. With E(epsilon|X)=0, the estimator is conditionally unbiased; with Var(epsilon|X)=sigma^2 I, its conditional covariance is sigma^2(X'X)^(-1).

Ridge adds lambda ||beta||^2/2 and yields beta_hat_lambda=(X'X+lambda I)^(-1)X'y. The positive ridge term guarantees a unique solution. Report lambda selection by time-based validation, not by test performance.

## ARMA and GARCH

For AR(1), x_t=c+phi x_(t-1)+epsilon_t, |phi|<1 gives x_t=c/(1-phi)+sum_{j>=0}phi^j epsilon_(t-j), with variance sigma^2/(1-phi^2). ARMA models target conditional means.

For GARCH(1,1), r_t=mu_t+sigma_t z_t and sigma_t^2=omega+alpha r_(t-1)^2+beta sigma_(t-1)^2. Under nonnegative parameters and alpha+beta<1, the unconditional variance is omega/(1-alpha-beta). Estimate by conditional likelihood and diagnose standardized residuals and squared residuals.

## Classification and quantiles

Logistic regression uses p=sigma(X beta). Cross-entropy is the Bernoulli negative log-likelihood; its gradient is X'(p-y), and its Hessian is X' W X. The expected pinball loss E[rho_alpha(Y-q)] has derivative F(q)-alpha, so its minimizer is the alpha-quantile.

## Neural sequence models

For an RNN, h_t=phi(W_x x_t+W_h h_(t-1)+b). Backpropagation contains products of W_h and phi', explaining exploding/vanishing gradients. LSTM introduces gates i_t,f_t,o_t and state c_t=f_t*c_(t-1)+i_t*c_tilde; the direct state derivative is f_t.

Causal convolution uses z_t=sum_j w_j x_(t-j), and its receptive field grows with layers and dilation. A causal Transformer uses A=softmax((QK'+M)/sqrt(d)) with M_ij=-infinity for j>i; this makes attention at i independent of future positions.

## Representation learning and graphs

A centered linear autoencoder with rank-k code recovers the principal subspace of PCA. Nonlinear autoencoders optimize reconstruction, not necessarily return prediction. A GCN layer is H_(l+1)=phi(Dtilde^(-1/2) Atilde Dtilde^(-1/2) H_l W_l). Build A inside each historical window if it is estimated from prices or correlations.

## Probabilistic and Bayesian models

For a Student-t head, optimize conditional negative log likelihood with positive scale. For Bayesian linear regression with beta~N(0,tau^2 I) and y|beta~N(X beta,sigma^2 I), posterior precision is X'X/sigma^2+I/tau^2. The posterior mean has the same algebraic form as ridge. Variational inference maximizes the ELBO, log p(y)=ELBO+KL(q||posterior).

For an ensemble, total predictive variance follows the law of total variance: average within-model variance plus variance of model means. Do not call ensemble spread a calibrated posterior without checking calibration.

## Portfolio and risk optimization

Mean-variance optimization maximizes mu'w-gamma w'Sigma w/2 under stated constraints. With budget only and Sigma positive definite, KKT conditions give the unique global optimizer. For CVaR, use min_zeta [zeta + E[(L-zeta)_+]/(1-alpha)] and sample auxiliary variables to obtain a convex program when the loss is convex.

Always separate forecast from decision. Forecast errors, covariance error, transaction costs, and infeasible constraints all affect the final portfolio.

## Pricing and reinforcement learning

In a binomial model, replication of (V_u,V_d) with Delta shares and bond B gives V_0=R^(-1)[q V_u+(1-q)V_d], q=(R-d)/(u-d). In Black--Scholes, Ito's lemma and delta hedging give V_t+sigma^2 S^2 V_SS/2+r S V_S-rV=0. Historical return probabilities are not automatically risk-neutral probabilities.

For reinforcement learning, Bellman expectation is V^pi(s)=E[r+gamma V^pi(s')|s], and the policy-gradient identity is grad J=E[sum_t grad log pi(a_t|s_t) G_t]. Offline financial data do not identify arbitrary counterfactual actions; require a credible simulator, conservative offline evaluation, and a fallback.

