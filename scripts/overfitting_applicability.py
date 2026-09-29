#!/usr/bin/env python3
"""Decide which backtest-overfitting diagnostics are applicable to a run."""
import argparse
import json
import math
from pathlib import Path

import numpy as np


METHODS = ("DM", "WRC", "SPA", "DSR", "PBO")


def moving_block_bootstrap(values, block_length=5, replications=1000, seed=7):
    """Generate dependent bootstrap samples by drawing circular blocks."""
    values = np.asarray(values, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    if values.shape[0] == 0 or block_length < 1:
        raise ValueError("bootstrap requires observations and a positive block length")
    rng = np.random.default_rng(seed)
    blocks = [values[(start + np.arange(block_length)) % len(values)] for start in range(len(values))]
    samples = []
    for _ in range(replications):
        selected = []
        while len(selected) < len(values):
            selected.extend(blocks[int(rng.integers(0, len(blocks)))])
        samples.append(np.asarray(selected[:len(values)]))
    return np.asarray(samples)


def _normal_sf(value):
    return 0.5 * math.erfc(float(value) / math.sqrt(2.0))


def dm_test(loss_a, loss_b, block_length=5, replications=1000, seed=7):
    """Diebold-Mariano test with a HAC variance and moving-block CI."""
    differential = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    if differential.size < 20 or differential.size != np.asarray(loss_b).size:
        return {"status": "failed", "reason": "paired loss vectors must have equal length >= 20"}
    mean = float(differential.mean())
    centered = differential - mean
    variance = float(np.mean(centered ** 2))
    for lag in range(1, min(block_length - 1, len(differential) - 1) + 1):
        variance += 2.0 * (1.0 - lag / (block_length + 1.0)) * float(np.mean(centered[lag:] * centered[:-lag]))
    variance = max(variance, 1e-14)
    statistic = mean / math.sqrt(variance / len(differential))
    samples = moving_block_bootstrap(differential, block_length, replications, seed)[:, 0].mean(axis=1)
    interval = np.quantile(samples, [0.025, 0.975]).tolist()
    p_value = min(1.0, 2.0 * _normal_sf(abs(statistic)))
    return {"status": "passed", "method": "DM", "statistic": float(statistic), "p_value": float(p_value), "confidence_interval": [float(interval[0]), float(interval[1])], "block_length": block_length, "replications": replications, "n": int(len(differential)), "interpretation": "reject equal predictive accuracy" if p_value < 0.05 else "insufficient evidence of a loss difference"}


def white_reality_check(candidate_returns, block_length=5, replications=1000, seed=7):
    """White's Reality Check for the maximum mean net return across candidates."""
    values = np.asarray(candidate_returns, dtype=float)
    if values.ndim != 2 or values.shape[1] < 3 or values.shape[0] < 30:
        return {"status": "failed", "reason": "WRC requires >=3 candidate return series and >=30 observations"}
    centered = values - values.mean(axis=0, keepdims=True)
    observed = float(values.mean(axis=0).max())
    boot = moving_block_bootstrap(centered, block_length, replications, seed).mean(axis=1).max(axis=1)
    p_value = float((1.0 + np.sum(boot >= observed)) / (replications + 1.0))
    interval = np.quantile(boot, [0.025, 0.975]).tolist()
    return {"status": "passed", "method": "WRC", "statistic": observed, "p_value": p_value, "confidence_interval": [float(interval[0]), float(interval[1])], "block_length": block_length, "replications": replications, "n": int(values.shape[0]), "candidate_count": int(values.shape[1]), "interpretation": "candidate family survives the reality check" if p_value < 0.05 else "family-level outperformance is not established"}


def spa_test(candidate_returns, block_length=5, replications=1000, seed=7):
    """Hansen SPA-style studentized superior predictive ability diagnostic."""
    values = np.asarray(candidate_returns, dtype=float)
    if values.ndim != 2 or values.shape[1] < 3 or values.shape[0] < 30:
        return {"status": "failed", "reason": "SPA requires >=3 candidate return series and >=30 observations"}
    means = values.mean(axis=0)
    standard_errors = np.maximum(values.std(axis=0, ddof=1) / math.sqrt(values.shape[0]), 1e-12)
    observed = float(np.max(np.maximum(means, 0.0) / standard_errors))
    centered = values - means
    boot = moving_block_bootstrap(centered, block_length, replications, seed)
    boot_stat = np.max(np.maximum(boot.mean(axis=1), 0.0) / standard_errors, axis=1)
    p_value = float((1.0 + np.sum(boot_stat >= observed)) / (replications + 1.0))
    return {"status": "passed", "method": "SPA", "statistic": observed, "p_value": p_value, "confidence_interval": [float(np.quantile(boot_stat, 0.025)), float(np.quantile(boot_stat, 0.975))], "block_length": block_length, "replications": replications, "n": int(values.shape[0]), "candidate_count": int(values.shape[1]), "interpretation": "superior predictive ability supported" if p_value < 0.05 else "superior predictive ability not established"}


def deflated_sharpe_ratio(returns, trials=1, skew=0.0, kurtosis=3.0):
    """Approximate Deflated Sharpe Ratio using the expected maximum Sharpe."""
    values = np.asarray(returns, dtype=float).ravel()
    if values.size < 30 or trials < 1:
        return {"status": "failed", "reason": "DSR requires >=30 net-of-cost observations"}
    sharpe = float(values.mean() / max(values.std(ddof=1), 1e-12) * math.sqrt(252))
    expected_max = math.sqrt(2.0 * math.log(max(1, trials)))
    variance = (1.0 - skew * sharpe + (kurtosis - 1.0) * sharpe * sharpe / 4.0) / max(values.size - 1, 1)
    z = (sharpe - expected_max) / math.sqrt(max(variance, 1e-12))
    p_value = float(_normal_sf(z))
    return {"status": "passed", "method": "DSR", "statistic": sharpe, "deflated_sharpe": float(z), "p_value": p_value, "confidence_interval": [float(sharpe - 1.96 * math.sqrt(max(variance, 1e-12))), float(sharpe + 1.96 * math.sqrt(max(variance, 1e-12)))], "trials": int(trials), "n": int(values.size), "interpretation": "Sharpe survives multiple-testing deflation" if p_value < 0.05 else "Sharpe is not significant after deflation"}


def probability_of_backtest_overfitting(candidate_returns, splits=8):
    """Estimate PBO by selecting on train halves and checking test underperformance."""
    values = np.asarray(candidate_returns, dtype=float)
    if values.ndim != 2 or values.shape[1] < 3 or values.shape[0] < 40 or splits < 2:
        return {"status": "failed", "reason": "PBO requires >=3 candidates, >=40 observations and >=2 splits"}
    half = values.shape[0] // 2
    outcomes = []
    for index in range(splits):
        order = np.roll(np.arange(values.shape[0]), index * max(1, values.shape[0] // splits))
        train, test = values[order[:half]], values[order[half:]]
        selected = int(np.argmax(train.mean(axis=0)))
        outcomes.append(float(test[:, selected].mean() < np.median(test.mean(axis=0))))
    probability = float(np.mean(outcomes))
    return {"status": "passed", "method": "PBO", "statistic": probability, "p_value": probability, "confidence_interval": [float(max(0.0, probability - 1.96 * math.sqrt(probability * (1 - probability) / len(outcomes)))), float(min(1.0, probability + 1.96 * math.sqrt(probability * (1 - probability) / len(outcomes))))], "splits": int(splits), "n": int(values.shape[0]), "candidate_count": int(values.shape[1]), "interpretation": "high overfitting probability" if probability > 0.5 else "overfitting probability is not dominant"}


def assess_applicability(candidate_count, trial_count, observations, paired_loss=False, portfolio_returns=False, diagnostic_inputs=None):
    """Trigger diagnostics and verify the inputs needed to make them real.

    The original booleans remain supported for backwards compatibility.  A
    caller that has run a backtest should pass ``diagnostic_inputs`` with
    paired losses, candidate family, net-of-cost returns, PBO split count and
    bootstrap block length.  Applicable-but-invalid diagnostics are blocking;
    not-applicable diagnostics remain neutral.
    """
    diagnostic_inputs = diagnostic_inputs or {}
    paired_losses = diagnostic_inputs.get("paired_losses")
    candidate_family = diagnostic_inputs.get("candidate_family")
    net_of_costs = diagnostic_inputs.get("net_of_costs")
    pbo_splits = diagnostic_inputs.get("pbo_splits")
    block_length = diagnostic_inputs.get("bootstrap_block_length")
    rules = {
        "DM": (candidate_count >= 2 and observations >= 20 and paired_loss, "requires paired losses for at least two candidates and 20 observations"),
        "WRC": (candidate_count >= 3 and trial_count >= 2 and observations >= 30, "requires a candidate family, multiple trials, and 30 observations"),
        "SPA": (candidate_count >= 3 and trial_count >= 2 and observations >= 30, "requires a candidate family, multiple trials, and 30 observations"),
        "DSR": (portfolio_returns and trial_count >= 2 and observations >= 30, "requires portfolio returns and multiple Sharpe trials"),
        "PBO": (candidate_count >= 3 and trial_count >= 2 and observations >= 40, "requires multiple candidates/trials and combinatorial sample size"),
    }
    methods = []
    input_checks = {
        "DM": bool(paired_loss and (paired_losses is None or len(paired_losses) >= 20)),
        "WRC": bool(candidate_family or candidate_count >= 3),
        "SPA": bool(candidate_family or candidate_count >= 3),
        "DSR": bool(portfolio_returns and (net_of_costs is None or net_of_costs is True)),
        "PBO": bool((pbo_splits is None or pbo_splits >= 2) and (block_length is None or block_length >= 2)),
    }
    input_reasons = {
        "DM": "paired loss observations are present",
        "WRC": "candidate family is declared",
        "SPA": "candidate family is declared",
        "DSR": "portfolio returns are net of costs",
        "PBO": "PBO split count and bootstrap block length are defined",
    }
    for method in METHODS:
        applicable, rule = rules[method]
        valid_input = input_checks[method]
        status = "not_applicable" if not applicable else ("pending" if valid_input else "failed")
        blocking = "selection_blocker" if applicable and not valid_input else ("selection_blocker" if applicable else "none")
        reason = "inputs satisfy the trigger rule" if applicable else rule
        if applicable and not valid_input:
            reason = "applicable diagnostic has incomplete or invalid inputs: " + input_reasons[method]
        methods.append({
            "method": method,
            "applicable": applicable,
            "reason": reason,
            "applicability_reason": "inputs satisfy the trigger rule" if applicable else rule,
            "input_requirements": [rule, input_reasons[method]],
            "input_valid": valid_input,
            "blocking_level": blocking,
            "status": status,
            "interpretation": "run this diagnostic before selection" if applicable else "not triggered for this research design",
        })
    applicable_count = sum(item["applicable"] for item in methods)
    invalid_count = sum(item["applicable"] and not item["input_valid"] for item in methods)
    return {"candidate_count": candidate_count, "trial_count": trial_count, "observations": observations, "methods": methods, "gate_status": "failed" if invalid_count else ("pending" if applicable_count else "not_triggered")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-count", type=int, required=True)
    parser.add_argument("--trial-count", type=int, required=True)
    parser.add_argument("--observations", type=int, required=True)
    parser.add_argument("--paired-loss", action="store_true")
    parser.add_argument("--portfolio-returns", action="store_true")
    parser.add_argument("--candidate-family", action="store_true")
    parser.add_argument("--net-of-costs", action="store_true")
    parser.add_argument("--pbo-splits", type=int, default=None)
    parser.add_argument("--bootstrap-block-length", type=int, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assess_applicability(args.candidate_count, args.trial_count, args.observations, args.paired_loss, args.portfolio_returns, {"candidate_family": args.candidate_family, "net_of_costs": args.net_of_costs, "pbo_splits": args.pbo_splits, "bootstrap_block_length": args.bootstrap_block_length})
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
