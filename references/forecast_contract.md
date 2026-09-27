# Forecast hierarchy and validity

Declare whether the output is a point, interval, quantile, probability, distribution, or volatility forecast. Use target-matched proper metrics: MAE/RMSE/MASE, coverage/width/interval score, pinball loss, log loss/Brier/calibration, CRPS/log score, or QLIKE respectively.

Raw price targets require a warning and a return/log-return/excess-return baseline. Candidate combinations are recorded as simple average, inverse-error weighted, or regime-conditional; the final result must retain the individual candidates and weights. A feature-distribution OOD flag is a validity status, not an automatic retraining authorization. Retraining creates a new experiment and reruns preflight.
