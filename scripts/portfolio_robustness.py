#!/usr/bin/env python3
"""Small covariance and fallback utilities; optimization remains config-driven."""
import numpy as np


def sample_covariance(returns):
    return np.atleast_2d(np.cov(np.asarray(returns), rowvar=False, ddof=1))


def ledoit_wolf_shrinkage(returns, shrinkage=0.1):
    cov = sample_covariance(returns)
    target = np.eye(cov.shape[0]) * np.trace(cov) / cov.shape[0]
    return (1 - shrinkage) * cov + shrinkage * target


def factor_covariance(returns, n_factors=1):
    data = np.asarray(returns, dtype=float)
    centered = data - data.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    loadings = vt[:n_factors].T
    factors = centered @ loadings
    residual = centered - factors @ loadings.T
    return np.cov(factors, rowvar=False, ddof=1) if loadings.shape[1] == 1 and loadings.shape[0] == 1 else loadings @ np.atleast_2d(np.cov(factors, rowvar=False, ddof=1)) @ loadings.T + np.diag(np.var(residual, axis=0, ddof=1))


def robust_covariance(returns, lower=0.01, upper=0.99):
    data = np.asarray(returns, dtype=float)
    clipped = np.clip(data, np.quantile(data, lower, axis=0), np.quantile(data, upper, axis=0))
    return sample_covariance(clipped)


def infeasible_fallback(solver_status, prior_weights, action="prior_weights"):
    if str(solver_status).lower() in {"optimal", "feasible"}:
        return {"used": False, "action": None, "reason": None, "weights": prior_weights}
    return {"used": True, "action": action, "reason": f"solver_status={solver_status}", "weights": prior_weights}
