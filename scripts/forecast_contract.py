"""Forecast target checks, forecast combinations, and simple OOD flags."""
from __future__ import annotations

import math
from typing import Mapping, Sequence

import numpy as np


METRICS = {
    "point": ["MAE", "RMSE", "MASE"],
    "interval": ["coverage", "width", "interval_score"],
    "quantile": ["pinball_loss"],
    "probability": ["log_loss", "Brier", "calibration"],
    "distribution": ["CRPS", "log_score"],
    "volatility": ["QLIKE", "volatility_loss"],
}


def target_check(target, columns):
    columns = set(columns or [])
    warnings = []
    if target == "price" and {"close", "adjusted_close"}.intersection(columns):
        warnings.append("price targets can create scale and non-stationarity problems; compare return/log_return/excess_return baselines")
    return {"target": target, "warnings": warnings, "status": "warning" if warnings else "ok"}


def build_forecast_contract(target, forecast_types=("point",), ood_status="not_checked", model_age=None, last_retrained_at=None):
    forecast_types = list(dict.fromkeys(forecast_types))
    return {
        "target": target,
        "forecast_types": forecast_types,
        "metrics": {kind: METRICS[kind] for kind in forecast_types},
        "validity_conditions": ["point-in-time-safe features", "rolling out-of-sample evaluation", "target-specific metric selection"],
        "known_failure_modes": ["regime drift", "out-of-distribution features", "target definition mismatch"],
        "ood_status": ood_status,
        "model_age": model_age,
        "last_retrained_at": last_retrained_at,
    }


def combine_forecasts(predictions: Mapping[str, Sequence[float]], errors=None, method="simple_average", regime=None):
    if not predictions:
        raise ValueError("predictions must contain at least one candidate")
    names = list(predictions)
    matrix = np.asarray([predictions[name] for name in names], dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] == 0:
        raise ValueError("predictions must be non-empty equal-length sequences")
    if method == "simple_average":
        weights = np.ones(len(names)) / len(names)
    elif method == "inverse_error":
        if not errors:
            raise ValueError("inverse_error requires errors")
        inverse = np.asarray([1.0 / max(float(errors[name]), 1e-12) for name in names])
        weights = inverse / inverse.sum()
    elif method == "regime_conditional":
        if not regime or not isinstance(regime, Mapping):
            raise ValueError("regime_conditional requires regime weights")
        weights = np.asarray([float(regime.get(name, 0.0)) for name in names])
        if weights.sum() <= 0:
            raise ValueError("regime weights must contain positive mass")
        weights /= weights.sum()
    else:
        raise ValueError("supported methods: simple_average, inverse_error, regime_conditional")
    return {"method": method, "models": names, "weights": weights.round(10).tolist(), "forecast": np.average(matrix, axis=0, weights=weights).tolist()}


def assess_ood(reference, current, threshold=0.2):
    """Use a bounded standardized mean shift as an auditable OOD proxy."""
    shifts = {}
    for name, values in (current or {}).items():
        ref = np.asarray((reference or {}).get(name, []), dtype=float)
        cur = np.asarray(values, dtype=float)
        if ref.size == 0 or cur.size == 0:
            continue
        scale = float(np.std(ref, ddof=1)) if ref.size > 1 else 0.0
        shifts[name] = abs(float(np.mean(cur) - np.mean(ref))) / max(scale, 1e-12)
    maximum = max(shifts.values(), default=0.0)
    status = "out_of_distribution" if maximum > threshold else ("warning" if maximum > threshold / 2 else "in_distribution")
    return {"ood_status": status, "threshold": threshold, "max_standardized_shift": maximum, "feature_shifts": shifts}
