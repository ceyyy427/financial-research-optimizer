#!/usr/bin/env python3
"""Decide which backtest-overfitting diagnostics are applicable to a run."""
import argparse
import json
from pathlib import Path


METHODS = ("DM", "WRC", "SPA", "DSR", "PBO")


def assess_applicability(candidate_count, trial_count, observations, paired_loss=False, portfolio_returns=False):
    rules = {
        "DM": (candidate_count >= 2 and observations >= 20 and paired_loss, "requires paired losses for at least two candidates and 20 observations"),
        "WRC": (candidate_count >= 3 and trial_count >= 2 and observations >= 30, "requires a candidate family, multiple trials, and 30 observations"),
        "SPA": (candidate_count >= 3 and trial_count >= 2 and observations >= 30, "requires a candidate family, multiple trials, and 30 observations"),
        "DSR": (portfolio_returns and trial_count >= 2 and observations >= 30, "requires portfolio returns and multiple Sharpe trials"),
        "PBO": (candidate_count >= 3 and trial_count >= 2 and observations >= 40, "requires multiple candidates/trials and combinatorial sample size"),
    }
    methods = []
    for method in METHODS:
        applicable, rule = rules[method]
        methods.append({
            "method": method,
            "applicable": applicable,
            "reason": "inputs satisfy the trigger rule" if applicable else rule,
            "applicability_reason": "inputs satisfy the trigger rule" if applicable else rule,
            "input_requirements": [rule],
            "blocking_level": "selection_blocker" if applicable else "none",
            "status": "pending" if applicable else "not_applicable",
            "interpretation": "run this diagnostic before selection" if applicable else "not triggered for this research design",
        })
    applicable_count = sum(item["applicable"] for item in methods)
    return {"candidate_count": candidate_count, "trial_count": trial_count, "observations": observations, "methods": methods, "gate_status": "pending" if applicable_count else "not_triggered"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-count", type=int, required=True)
    parser.add_argument("--trial-count", type=int, required=True)
    parser.add_argument("--observations", type=int, required=True)
    parser.add_argument("--paired-loss", action="store_true")
    parser.add_argument("--portfolio-returns", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assess_applicability(args.candidate_count, args.trial_count, args.observations, args.paired_loss, args.portfolio_returns)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
