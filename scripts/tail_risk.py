#!/usr/bin/env python3
"""Tail-risk estimators and dependent-observation uncertainty utilities.

The module deliberately keeps extreme observations.  ``robust_covariance`` may
down-weight observations for covariance estimation, but it must not be used as
a substitute for tail-risk measurement.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def _losses(losses: Iterable[float]) -> np.ndarray:
    values = np.asarray(list(losses), dtype=float).reshape(-1)
    if values.size < 2:
        raise ValueError("at least two finite losses are required")
    if not np.all(np.isfinite(values)):
        raise ValueError("losses must be finite")
    return values


def empirical_tail_risk(losses: Iterable[float], alpha: float = 0.95) -> dict:
    """Return VaR, CVaR/ES and conditional tail variance for a loss series.

    The empirical convention is ``L >= VaR_alpha``.  With this convention
    ``tail_variance`` and ``tail_conditional_variance`` are equal by design;
    both names are retained because reports often use the former for the
    portfolio risk measure and the latter for the mathematical conditional
    variance.
    """
    values = _losses(losses)
    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("alpha must be strictly between zero and one")
    threshold = float(np.quantile(values, alpha))
    tail = values[values >= threshold]
    variance = float(np.var(tail, ddof=1)) if tail.size > 1 else 0.0
    return {
        "estimator": "empirical",
        "alpha": float(alpha),
        "loss_definition": "negative_portfolio_return",
        "var": threshold,
        "cvar": float(np.mean(tail)),
        "tail_variance": variance,
        "tail_conditional_variance": variance,
        "tail_count": int(tail.size),
        "sample_size": int(values.size),
        "tail_fraction": float(tail.size / values.size),
        "definition": "Var(L | L >= VaR_alpha)",
        "status": "ok",
        "failure_boundary": "tail_count < 2 makes the conditional variance zero and requires a warning",
    }


def moving_block_sample(values: Iterable[float], block_length: int, rng=None) -> np.ndarray:
    """Draw one moving-block bootstrap sample with the original length."""
    data = _losses(values)
    block_length = int(block_length)
    if block_length < 1 or block_length > data.size:
        raise ValueError("block_length must be in [1, sample_size]")
    generator = rng if rng is not None else np.random.default_rng()
    starts = generator.integers(0, data.size - block_length + 1, size=math.ceil(data.size / block_length))
    sample = np.concatenate([data[start : start + block_length] for start in starts])
    return sample[: data.size]


def bootstrap_tail_risk(
    losses: Iterable[float],
    alpha: float = 0.95,
    replications: int = 2000,
    block_length: int = 20,
    seed: int = 7,
) -> dict:
    """Estimate percentile intervals using a moving-block bootstrap.

    The seed, block length and replication count are returned because they are
    part of the result lineage.  The method preserves local serial dependence;
    it is not an iid bootstrap.
    """
    values = _losses(losses)
    replications = int(replications)
    if replications < 1:
        raise ValueError("replications must be positive")
    if int(block_length) > values.size:
        raise ValueError("block_length cannot exceed sample_size")
    rng = np.random.default_rng(seed)
    draws = np.empty((replications, 3), dtype=float)
    for index in range(replications):
        metric = empirical_tail_risk(moving_block_sample(values, block_length, rng), alpha)
        draws[index] = [metric["var"], metric["cvar"], metric["tail_conditional_variance"]]
    interval = {
        key: [float(np.quantile(draws[:, col], 0.025)), float(np.quantile(draws[:, col], 0.975))]
        for col, key in enumerate(("var", "cvar", "tail_conditional_variance"))
    }
    interval["tail_variance"] = interval["tail_conditional_variance"]
    return {
        "method": "moving_block",
        "replications": replications,
        "block_length": int(block_length),
        "seed": int(seed),
        "confidence_level": 0.95,
        "intervals": interval,
        "status": "ok",
        "failure_boundary": "short samples or block_length greater than sample_size",
    }


def _normal_ppf(probability: float) -> float:
    """Acklam's rational approximation; avoids making scipy a core dependency."""
    if not 0.0 < probability < 1.0:
        raise ValueError("probability must be in (0, 1)")
    a = (-39.6968302866538, 220.946098424521, -275.928510446969, 138.357751867269, -30.6647980661472, 2.50662827745924)
    b = (-54.4760987982241, 161.585836858041, -155.698979859887, 66.8013118877197, -13.2806815528857)
    c = (-0.00778489400243029, -0.322396458041136, -2.40075827716184, -2.54973253934373, 4.37466414146497, 2.93816398269878)
    d = (0.00778469570904146, 0.32246712907004, 2.445134137143, 3.75440866190742)
    def poly(coefficients, x):
        result = 0.0
        for coefficient in coefficients:
            result = result * x + coefficient
        return result

    if probability < 0.02425:
        q = math.sqrt(-2 * math.log(probability))
        return poly(c, q) / (poly(d, q) * q + 1)
    if probability > 1 - 0.02425:
        return -_normal_ppf(1 - probability)
    q = probability - 0.5
    r = q * q
    return poly(a, r) * q / (poly(b, r) * r + 1)


def gaussian_tail_risk(losses: Iterable[float], alpha: float = 0.95) -> dict:
    """Parametric Gaussian tail risk, including the truncated-normal variance."""
    values = _losses(losses)
    mean = float(np.mean(values))
    scale = float(np.std(values, ddof=1))
    if scale <= 0:
        raise ValueError("Gaussian scale must be positive")
    z = _normal_ppf(float(alpha))
    density = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    tail_probability = 1 - float(alpha)
    mills = density / tail_probability
    conditional_variance = scale * scale * max(0.0, 1 + z * mills - mills * mills)
    return {
        "estimator": "gaussian",
        "alpha": float(alpha),
        "parameters": {"mean": mean, "scale": scale},
        "var": mean + scale * z,
        "cvar": mean + scale * mills,
        "tail_variance": conditional_variance,
        "tail_conditional_variance": conditional_variance,
        "status": "ok",
        "failure_boundary": "invalid under materially non-Gaussian tails; compare with empirical and heavy-tail candidates",
    }


DISTRIBUTION_REGISTRY = {
    "empirical": {"estimator": "sample quantile and conditional moments", "pit": "empirical randomized PIT", "failure_boundary": "too few tail observations"},
    "gaussian": {"estimator": "mean and sample standard deviation", "pit": "normal PIT", "failure_boundary": "skew or heavy tails"},
    "student_t": {"estimator": "maximum likelihood or robust moment fit", "pit": "t PIT", "failure_boundary": "unstable degrees of freedom with short samples"},
    "generalized_laplace": {"estimator": "declared likelihood or quantile fit", "pit": "generalized-Laplace PIT", "failure_boundary": "identifiability and tail-parameter instability"},
    "elliptical_mixture": {"estimator": "component likelihood/EM inside the training window", "pit": "mixture PIT", "failure_boundary": "component label switching and weakly identified regimes"},
}


def compare_distribution_candidates(losses: Iterable[float], alpha: float = 0.95, candidates=None) -> dict:
    """Return an auditable distribution comparison without fabricating fits.

    Core dependencies implement empirical and Gaussian fits.  The other
    registered families are explicit ``not_available`` challengers until a
    declared likelihood implementation is supplied; this is preferable to
    silently treating a Gaussian approximation as a generalized Laplace fit.
    """
    values = _losses(losses)
    names = list(candidates or DISTRIBUTION_REGISTRY)
    rows = []
    for name in names:
        if name not in DISTRIBUTION_REGISTRY:
            rows.append({"distribution": name, "status": "not_available", "reason": "not registered"})
            continue
        if name == "empirical":
            result = empirical_tail_risk(values, alpha)
            rows.append({"distribution": name, **result, "pit_status": "diagnostic_required"})
        elif name == "gaussian":
            result = gaussian_tail_risk(values, alpha)
            rows.append({"distribution": name, **result, "pit_status": "diagnostic_required"})
        else:
            rows.append({"distribution": name, "status": "not_available", "reason": "likelihood implementation is not enabled in the core runtime", "failure_boundary": DISTRIBUTION_REGISTRY[name]["failure_boundary"]})
    return {"alpha": float(alpha), "candidates": rows, "registry": DISTRIBUTION_REGISTRY, "status": "ok"}
