"""Portfolio benchmark, attribution and fragility diagnostics."""
from __future__ import annotations

import numpy as np


def benchmark_weights(n_assets, kind="equal_weight", market_cap=None, covariance=None):
    if n_assets < 1:
        raise ValueError("n_assets must be positive")
    if kind == "equal_weight":
        return np.ones(n_assets) / n_assets
    if kind == "market_cap":
        values = np.asarray(market_cap, dtype=float)
        if values.size != n_assets or values.sum() <= 0:
            raise ValueError("market_cap benchmark requires positive weights for every asset")
        return values / values.sum()
    if kind == "minimum_variance":
        if covariance is None:
            raise ValueError("minimum_variance benchmark requires covariance")
        inv = np.linalg.pinv(np.asarray(covariance, dtype=float))
        raw = inv @ np.ones(n_assets)
        return raw / raw.sum()
    if kind == "risk_parity":
        if covariance is None:
            raise ValueError("risk_parity benchmark requires covariance")
        vol = np.sqrt(np.maximum(np.diag(np.asarray(covariance, dtype=float)), 1e-12))
        raw = 1.0 / vol
        return raw / raw.sum()
    raise ValueError("unsupported benchmark")


def risk_contribution(weights, covariance):
    weights = np.asarray(weights, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    marginal = covariance @ weights
    total = float(weights @ marginal)
    if total <= 0:
        return np.zeros_like(weights)
    return weights * marginal / total


def fragility_report(weights, prior_weights=None, covariance=None, weight_scenarios=None, turnover_limit=None):
    weights = np.asarray(weights, dtype=float)
    reasons = []
    if weights.size and float(np.max(np.abs(weights))) > 0.8:
        reasons.append("single_asset_concentration")
    if weights.size and float(np.min(weights)) < -0.5:
        reasons.append("extreme_negative_weight")
    if covariance is not None and np.linalg.cond(np.asarray(covariance, dtype=float)) > 1e8:
        reasons.append("near_singular_covariance")
    turnover = None
    if prior_weights is not None:
        turnover = float(np.abs(weights - np.asarray(prior_weights, dtype=float)).sum())
        if turnover_limit is not None and turnover > float(turnover_limit):
            reasons.append("turnover_limit")
    interval = None
    if weight_scenarios:
        matrix = np.asarray(weight_scenarios, dtype=float)
        interval = {f"asset_{i}": [float(np.min(matrix[:, i])), float(np.max(matrix[:, i]))] for i in range(matrix.shape[1])}
        if np.max(np.ptp(matrix, axis=0), initial=0.0) > 0.25:
            reasons.append("weight_instability")
    return {"status": "portfolio_fragile" if reasons else "stable", "reasons": reasons, "turnover": turnover, "weight_intervals": interval}


def constraint_diagnostics(weights, constraints):
    weights = np.asarray(weights, dtype=float)
    rows = []
    if "max_weight" in constraints:
        limit = float(constraints["max_weight"])
        for index, value in enumerate(weights):
            rows.append({"constraint": "max_weight", "asset_index": index, "limit": limit, "solution": float(value), "binding": bool(abs(value - limit) <= 1e-8), "marginal_value": None, "interpretation": "weight cap limits the unconstrained allocation"})
    return rows
