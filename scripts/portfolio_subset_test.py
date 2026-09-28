#!/usr/bin/env python3
"""Block-bootstrap test for whether candidate assets expand a base opportunity set."""
from __future__ import annotations

import numpy as np

from tail_risk import moving_block_sample


def _matrix(values, name):
    data = np.asarray(values, dtype=float)
    if data.ndim == 1:
        data = data[:, None]
    if data.ndim != 2 or data.shape[0] < 20 or data.shape[1] < 1 or not np.all(np.isfinite(data)):
        raise ValueError(f"{name} must be a finite matrix with at least 20 rows")
    return data


def _sharpe(values):
    values = np.asarray(values, dtype=float)
    scale = float(np.std(values, ddof=1))
    return float(np.mean(values) / scale) if scale > 0 else 0.0


def _opportunity_statistic(base, candidate, risk_free=None):
    """Use the increase in best single-asset Sharpe as a conservative screen.

    This is a screening statistic, not the full Huberman--Kandel spanning test.
    A production spanning implementation may replace it while preserving the
    contract and bootstrap protocol.
    """
    excess_base = base - (risk_free[:, None] if risk_free is not None else 0.0)
    excess_candidate = candidate - (risk_free[:, None] if risk_free is not None else 0.0)
    base_score = max((_sharpe(excess_base[:, i]) for i in range(excess_base.shape[1])), default=0.0)
    full = np.column_stack([excess_base, excess_candidate])
    full_score = max((_sharpe(full[:, i]) for i in range(full.shape[1])), default=0.0)
    return max(0.0, float(full_score - base_score))


def effective_asset_subset_test(
    base_returns,
    candidate_returns,
    risk_free=None,
    alpha: float = 0.05,
    block_length: int = 20,
    replications: int = 2000,
    seed: int = 7,
    allow_short: bool = False,
    rolling_windows=None,
) -> dict:
    """Test H0: candidates do not expand the base mean-variance opportunity set.

    The statistic is a conservative opportunity-set expansion screen.  Its
    validity depends on pre-registering the candidate family and preserving
    serial dependence with moving blocks.  It must not be interpreted as a
    claim that a rejected null guarantees future returns.
    """
    base = _matrix(base_returns, "base_returns")
    candidate = _matrix(candidate_returns, "candidate_returns")
    if base.shape[0] != candidate.shape[0]:
        raise ValueError("base_returns and candidate_returns must share rows")
    if not 0 < float(alpha) < 1:
        raise ValueError("alpha must be in (0, 1)")
    rf = None if risk_free is None else np.asarray(risk_free, dtype=float).reshape(-1)
    if rf is not None and (rf.size != base.shape[0] or not np.all(np.isfinite(rf))):
        raise ValueError("risk_free must have one finite value per row")
    if block_length < 1 or block_length > base.shape[0]:
        raise ValueError("block_length must be between one and sample size")
    observed = _opportunity_statistic(base, candidate, rf)
    rng = np.random.default_rng(seed)
    null_stats = np.empty(int(replications), dtype=float)
    # Under H0, residualize candidate series on the base span and resample the
    # residual blocks. This preserves common base shocks while removing the
    # candidate's unconditional incremental mean signal.
    x = np.column_stack([np.ones(base.shape[0]), base])
    fitted = x @ np.linalg.lstsq(x, candidate, rcond=None)[0]
    residual = candidate - fitted
    centered = base.copy()
    for index in range(null_stats.size):
        sample = moving_block_sample(np.arange(base.shape[0]), block_length, rng).astype(int)
        null_base = centered[sample]
        null_candidate = fitted[sample] + residual[sample]
        null_stats[index] = _opportunity_statistic(null_base, null_candidate, rf[sample] if rf is not None else None)
    p_value = float((1 + np.sum(null_stats >= observed)) / (null_stats.size + 1))
    interval = [float(np.quantile(null_stats, 0.025)), float(np.quantile(null_stats, 0.975))]
    windows = []
    for window in rolling_windows or []:
        start, end = int(window[0]), int(window[1])
        if not (0 <= start < end <= base.shape[0]) or end - start < 20:
            windows.append({"window": [start, end], "status": "not_available", "reason": "window is too short or outside sample"})
            continue
        statistic = _opportunity_statistic(base[start:end], candidate[start:end], rf[start:end] if rf is not None else None)
        windows.append({"window": [start, end], "test_statistic": statistic, "status": "ok", "spanning_status": "expanded" if statistic > 0 else "not_expanded"})
    significant = p_value < float(alpha)
    return {
        "null_hypothesis": "candidate assets cannot expand the base mean-variance opportunity set",
        "test_statistic": observed,
        "p_value": p_value,
        "alpha": float(alpha),
        "bootstrap_interval": interval,
        "spanning_status": "reject_null_candidate_expands_set" if significant else "fail_to_reject_null",
        "subset_status": "candidate_non_redundant" if significant else "base_subset_sufficient_under_protocol",
        "power_diagnostic": {"observations": int(base.shape[0]), "candidate_count": int(candidate.shape[1]), "base_count": int(base.shape[1]), "replications": int(replications), "block_length": int(block_length), "allow_short": bool(allow_short), "warning": "screening statistic; report power limitations for short or highly dependent samples"},
        "window_stability": {"windows": windows, "stable": bool(windows) and len({item.get("spanning_status") for item in windows if item.get("status") == "ok"}) <= 1},
        "bootstrap": {"method": "moving_block", "seed": int(seed), "replications": int(replications), "block_length": int(block_length)},
        "status": "ok",
    }

