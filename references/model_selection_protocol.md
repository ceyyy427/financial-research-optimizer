# Multi-criterion model selection protocol

Model selection is a declared protocol, not a single leaderboard. Score every candidate on five dimensions:

1. statistical validity: assumptions, residual diagnostics, calibration tests and applicable DM/WRC/SPA/DSR/PBO evidence;
2. predictive performance: rolling point/probability/tail metrics with uncertainty;
3. economic effectiveness: net return, risk-adjusted utility, turnover, costs and capacity;
4. regime stability: performance by regime, drawdown state and calendar slice;
5. seed/window sensitivity: dispersion across random seeds, train windows, horizons and reasonable perturbations;
6. degradation and benchmark stability: train-to-test degradation, benchmark-relative rank and feature-ablation impact.

Weights and minimum stability thresholds are frozen in `models.selection.criteria` and `selection_protocol`. A candidate is eligible only after statistical validity and applicability gates pass; the weighted score breaks ties among eligible candidates. If no candidate passes, the result is `wait` or `insufficient evidence`, never a silently selected winner.
