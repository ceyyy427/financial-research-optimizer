#!/usr/bin/env python3
"""Run the v1.1.0 release gate and fail closed on incomplete runtime claims."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(command, cwd):
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {"command": " ".join(command), "returncode": completed.returncode, "output": (completed.stdout + completed.stderr)[-4000:]}


def _behavioral_check(root):
    """Exercise critical claims instead of only checking that functions exist."""
    try:
        import numpy as np
        from scripts.overfitting_applicability import dm_test, white_reality_check, spa_test, deflated_sharpe_ratio, probability_of_backtest_overfitting
        from scripts.portfolio_robustness import solve_constrained_portfolio
        rng = np.random.default_rng(17)
        returns = rng.normal(0.001, 0.01, size=(80, 3))
        covariance = np.cov(returns, rowvar=False)
        solved = solve_constrained_portfolio(returns.mean(axis=0), covariance, {"long_only": True, "max_weight": 0.6, "max_turnover": 0.5}, [1 / 3] * 3, 1.0, 10.0)
        if solved.get("status") != "optimal" or not solved["constraints"].get("feasible") or max(solved["weights"]) > 0.6000001:
            return {"command": "behavioral", "returncode": 1, "output": "portfolio constraint behavior failed"}
        if solve_constrained_portfolio([0.1, 0.1, 0.1], np.eye(3), {"long_only": True, "max_weight": 0.2}, [1 / 3] * 3).get("status") != "infeasible":
            return {"command": "behavioral", "returncode": 1, "output": "infeasible portfolio was not blocked"}
        losses = rng.normal(size=(50, 3))
        diagnostics = [dm_test(losses[:, 0], losses[:, 1]), white_reality_check(returns), spa_test(returns), deflated_sharpe_ratio(returns[:, 0], 3), probability_of_backtest_overfitting(returns, 4)]
        if any(item.get("status") != "passed" for item in diagnostics):
            return {"command": "behavioral", "returncode": 1, "output": "statistical diagnostic behavior failed"}
        return {"command": "behavioral", "returncode": 0, "output": "portfolio constraints and DM/WRC/SPA/DSR/PBO executed"}
    except Exception as exc:
        return {"command": "behavioral", "returncode": 1, "output": str(exc)}


def _mode_contract_check():
    """Ensure each public mode has a non-empty plan and explicit artifacts."""
    from scripts.agent.planner import build_plan, create_research_contract

    modes = ("data_audit", "descriptive_analysis", "forecasting", "backtest", "portfolio_research")
    rows = {}
    for mode in modes:
        level = "research_grade" if mode in {"backtest", "portfolio_research"} else "standard"
        plan = build_plan(create_research_contract("release gate mode smoke", mode=mode, output_level=level))
        nodes = plan.get("nodes", plan.get("steps", [])) if isinstance(plan, dict) else []
        rows[mode] = {"node_count": len(nodes), "has_nodes": bool(nodes)}
    passed = all(row["has_nodes"] for row in rows.values())
    return {"command": "mode_contracts", "returncode": 0 if passed else 1, "output": json.dumps(rows)}


def release_gate(root=Path(".")):
    checks = []
    checks.append(_run([sys.executable, "-m", "pytest", "-q"], root))
    checks.append(_run([sys.executable, "scripts/validate_schemas.py"], root))
    checks.append(_run([sys.executable, "scripts/validate_source_registry.py", "--registry", "config/source_registry.yaml"], root))
    validator = Path("/Users/mac/.codex/skills/.system/skill-creator/scripts/quick_validate.py")
    if validator.exists():
        checks.append(_run([sys.executable, str(validator), str(root)], root))
    from scripts.agent.handlers import HANDLERS
    required_nodes = ["run_overfitting_diagnostics", "run_portfolio_optimization", "post_selection_stress_test"]
    missing_nodes = [name for name in required_nodes if name not in HANDLERS or getattr(HANDLERS[name], "__name__", "") == "handler"]
    from scripts.adapters.status import adapter_status
    maturity = adapter_status(root / "config/source_registry.yaml")
    checks.append({"command": "stable_nodes", "returncode": 0 if not missing_nodes else 1, "output": json.dumps({"missing_nodes": missing_nodes})})
    checks.append(_behavioral_check(root))
    checks.append(_mode_contract_check())
    checks.append({"command": "maturity", "returncode": 0 if maturity["live_certified_count"] >= 2 else 1, "output": json.dumps({key: maturity[key] for key in ("live_certified_count", "degraded_execution_count", "blocked_count")})})
    passed = all(item["returncode"] == 0 for item in checks)
    return {"schema_version": "1.0", "status": "passed" if passed else "blocked", "checks": checks, "maturity": {key: maturity[key] for key in ("automatic_execution_count", "live_certified_count", "degraded_execution_count", "manual_review_only_count", "blocked_count")}, "next_action": None if passed else "resolve release gate failures", "user_action_required": not passed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = release_gate(args.root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(0 if result["status"] == "passed" else 2)


if __name__ == "__main__":
    main()
