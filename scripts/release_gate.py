#!/usr/bin/env python3
"""Run the v1.0.0 release gate and fail closed on incomplete runtime claims."""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(command, cwd):
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {"command": " ".join(command), "returncode": completed.returncode, "output": (completed.stdout + completed.stderr)[-4000:]}


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
