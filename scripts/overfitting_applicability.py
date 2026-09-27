#!/usr/bin/env python3
"""Decide which backtest-overfitting diagnostics are applicable to a run."""
import argparse
import json
from pathlib import Path


METHODS = ("DM", "WRC", "SPA", "DSR", "PBO")


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
