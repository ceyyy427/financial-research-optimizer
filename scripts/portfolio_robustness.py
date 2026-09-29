#!/usr/bin/env python3
"""Covariance estimators and deterministic constrained portfolio optimization."""
import numpy as np


def sample_covariance(returns):
    data = np.asarray(returns, dtype=float)
    if data.ndim == 1:
        data = data[:, None]
    if data.shape[0] < 2:
        raise ValueError("at least two return observations are required")
    covariance = np.atleast_2d(np.cov(data, rowvar=False, ddof=1))
    return _nearest_psd(covariance)


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


def _nearest_psd(matrix, floor=1e-10):
    matrix = (np.asarray(matrix, dtype=float) + np.asarray(matrix, dtype=float).T) / 2.0
    eigenvalues, eigenvectors = np.linalg.eigh(matrix)
    return eigenvectors @ np.diag(np.maximum(eigenvalues, floor)) @ eigenvectors.T


def _project_capped_simplex(vector, total=1.0, lower=0.0, upper=1.0):
    """Project onto {w: sum(w)=total, lower<=w<=upper}."""
    vector = np.asarray(vector, dtype=float)
    if lower * vector.size > total + 1e-10 or upper * vector.size < total - 1e-10:
        raise ValueError("infeasible bounded simplex")
    lo, hi = float(np.min(vector - upper)), float(np.max(vector - lower))
    for _ in range(80):
        mid = (lo + hi) / 2.0
        candidate = np.clip(vector - mid, lower, upper)
        if candidate.sum() > total:
            lo = mid
        else:
            hi = mid
    return np.clip(vector - (lo + hi) / 2.0, lower, upper)


def validate_constraints(weights, constraints=None, prior_weights=None):
    """Return machine-checkable residuals for the declared portfolio constraints."""
    constraints = constraints or {}
    weights = np.asarray(weights, dtype=float)
    max_weight = float(constraints.get("max_weight", 1.0))
    min_weight = float(constraints.get("min_weight", 0.0 if constraints.get("long_only", True) else -max_weight))
    leverage_limit = float(constraints.get("leverage", constraints.get("max_leverage", 1.0)))
    turnover_limit = constraints.get("max_turnover", constraints.get("turnover_limit"))
    residuals = {
        "budget": float(abs(weights.sum() - float(constraints.get("budget", 1.0)))),
        "max_weight": float(max(0.0, np.max(weights, initial=0.0) - max_weight)),
        "min_weight": float(max(0.0, min_weight - np.min(weights, initial=0.0))),
        "leverage": float(max(0.0, np.abs(weights).sum() - leverage_limit)),
    }
    if constraints.get("long_only", True):
        residuals["long_only"] = float(max(0.0, -np.min(weights, initial=0.0)))
    if prior_weights is not None:
        turnover = float(np.abs(weights - np.asarray(prior_weights, dtype=float)).sum())
        residuals["turnover"] = float(max(0.0, turnover - float(turnover_limit))) if turnover_limit is not None else 0.0
    else:
        turnover = None
        residuals["turnover"] = 0.0
    industry = constraints.get("industry_exposure", {})
    industry_max = constraints.get("industry_max", {})
    if industry and industry_max:
        residuals["industry"] = float(max((max(0.0, abs(sum(weights[i] for i, group in enumerate(industry.values()) if group == name)) - float(limit)) for name, limit in industry_max.items()), default=0.0))
    factor_exposure = constraints.get("factor_exposure")
    factor_bounds = constraints.get("factor_bounds")
    if factor_exposure is not None and factor_bounds is not None:
        exposure = np.asarray(factor_exposure, dtype=float).T @ weights
        residuals["factor"] = float(max((max(0.0, abs(value) - float(bound)) for value, bound in zip(exposure, factor_bounds)), default=0.0))
    active = []
    if residuals["budget"] <= 1e-8:
        active.append("budget")
    if weights.size and abs(float(np.max(weights)) - max_weight) <= 1e-8:
        active.append("max_weight")
    if weights.size and abs(float(np.min(weights)) - min_weight) <= 1e-8:
        active.append("min_weight")
    if abs(float(np.abs(weights).sum()) - leverage_limit) <= 1e-8:
        active.append("leverage")
    if constraints.get("long_only", True) and weights.size and abs(float(np.min(weights))) <= 1e-8:
        active.append("long_only")
    if turnover_limit is not None and turnover is not None and abs(turnover - float(turnover_limit)) <= 1e-8:
        active.append("turnover")
    return {"feasible": bool(all(value <= 1e-7 for value in residuals.values())), "residuals": residuals, "active_constraints": active, "turnover": turnover}


def solve_constrained_portfolio(expected_returns, covariance, constraints=None, prior_weights=None, risk_aversion=1.0, transaction_cost_bps=0.0, max_iter=600):
    """Solve a bounded mean-variance-minus-cost problem without silently relaxing constraints."""
    constraints = dict(constraints or {})
    mu = np.asarray(expected_returns, dtype=float)
    covariance = _nearest_psd(covariance)
    n_assets = mu.size
    budget = float(constraints.get("budget", 1.0))
    long_only = bool(constraints.get("long_only", not constraints.get("allow_short", False)))
    upper = float(constraints.get("max_weight", budget if long_only else constraints.get("leverage", 1.0)))
    lower = float(constraints.get("min_weight", 0.0 if long_only else -upper))
    if prior_weights is None:
        prior = np.ones(n_assets) * budget / n_assets
    else:
        prior = np.asarray(prior_weights, dtype=float)
        if prior.size != n_assets:
            raise ValueError("prior_weights must match expected_returns")
    if long_only:
        try:
            weights = _project_capped_simplex(prior, budget, lower, upper)
        except ValueError as exc:
            return {"status": "infeasible", "reason": str(exc), "weights": prior.tolist(), "objective": None, "constraints": validate_constraints(prior, constraints, prior)}
    else:
        weights = np.clip(prior, lower, upper)
        weights += (budget - weights.sum()) / n_assets
    cost = float(transaction_cost_bps) / 10000.0
    scale = max(float(np.linalg.eigvalsh(covariance).max()), 1e-8)
    step = 0.25 / (risk_aversion * scale + 1.0)
    for _ in range(max_iter):
        gradient = mu - risk_aversion * (covariance @ weights)
        if cost and prior is not None:
            gradient -= cost * np.sign(weights - prior)
        candidate = weights + step * gradient
        if long_only:
            try:
                candidate = _project_capped_simplex(candidate, budget, lower, upper)
            except ValueError:
                return {"status": "infeasible", "reason": "bounded simplex is infeasible", "weights": weights.tolist(), "objective": None, "constraints": validate_constraints(weights, constraints, prior)}
        else:
            candidate = np.clip(candidate, lower, upper)
            candidate += (budget - candidate.sum()) / n_assets
        if constraints.get("max_turnover", constraints.get("turnover_limit")) is not None and prior is not None:
            limit = float(constraints.get("max_turnover", constraints.get("turnover_limit")))
            turnover = float(np.abs(candidate - prior).sum())
            if turnover > limit + 1e-10:
                alpha = limit / turnover if turnover else 0.0
                candidate = prior + alpha * (candidate - prior)
                if long_only:
                    candidate = _project_capped_simplex(candidate, budget, lower, upper)
        if np.max(np.abs(candidate - weights)) < 1e-10:
            weights = candidate
            break
        weights = candidate
    diagnostics = validate_constraints(weights, constraints, prior)
    objective = float(mu @ weights - 0.5 * risk_aversion * weights @ covariance @ weights - cost * np.abs(weights - prior).sum())
    if not diagnostics["feasible"]:
        return {"status": "infeasible", "reason": "constraint residual exceeds tolerance", "weights": weights.tolist(), "objective": objective, "constraints": diagnostics}
    return {"status": "optimal", "reason": None, "weights": weights.tolist(), "objective": objective, "constraints": diagnostics, "transaction_cost": cost * float(np.abs(weights - prior).sum())}


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
