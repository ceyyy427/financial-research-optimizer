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


def compare_covariance_models(returns):
    """Return a deterministic comparison table for the four supported estimators."""
    estimators = {
        "sample": sample_covariance,
        "ledoit_wolf": ledoit_wolf_shrinkage,
        "factor": factor_covariance,
        "robust": robust_covariance,
    }
    rows = []
    for name, estimator in estimators.items():
        covariance = np.asarray(estimator(returns), dtype=float)
        eigenvalues = np.linalg.eigvalsh((covariance + covariance.T) / 2)
        rows.append({
            "model": name,
            "condition_number": float(np.linalg.cond(covariance)),
            "minimum_eigenvalue": float(np.min(eigenvalues)),
            "positive_semidefinite": bool(np.min(eigenvalues) >= -1e-10),
        })
    return rows


def perturbation_ranges(weights_by_scenario, asset_names=None):
    """Summarize weight, turnover and objective intervals across scenarios."""
    matrix = np.asarray([item["weights"] for item in weights_by_scenario], dtype=float)
    names = list(asset_names or [f"asset_{index}" for index in range(matrix.shape[1])])
    return {
        "weight_intervals": {name: [float(matrix[:, index].min()), float(matrix[:, index].max())] for index, name in enumerate(names)},
        "turnover_interval": [float(min(item.get("turnover", 0.0) for item in weights_by_scenario)), float(max(item.get("turnover", 0.0) for item in weights_by_scenario))],
        "objective_interval": [float(min(item.get("objective", 0.0) for item in weights_by_scenario)), float(max(item.get("objective", 0.0) for item in weights_by_scenario))],
        "infeasible_reasons": sorted({reason for item in weights_by_scenario for reason in item.get("infeasible_reasons", [])}),
    }
