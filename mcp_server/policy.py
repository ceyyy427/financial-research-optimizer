"""Input and disclosure policy for the MCP boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

try:
    from scripts.agent.policy_guard import validate_task_scope
except ImportError:  # pragma: no cover - supports execution from scripts/
    from agent.policy_guard import validate_task_scope


MODES = {"data_audit", "descriptive_analysis", "forecasting", "backtest", "portfolio_research"}
OUTPUT_LEVELS = {"minimal", "standard", "research_grade", "portfolio_grade"}
MAX_TASK_CHARS = 2_000
MAX_UNIVERSE_ITEMS = 100
MAX_CONSTRAINT_BYTES = 20_000


@dataclass
class McpPolicyError(ValueError):
    """Structured, user-actionable error that is safe to return to an MCP host."""

    code: str
    message: str
    user_action_required: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {"status": "blocked", "reason_code": self.code, "message": self.message, "user_action_required": self.user_action_required}


def validate_create_request(
    task: str,
    mode: str,
    output_level: str,
    universe: list[str] | None = None,
    target: str | None = None,
    horizon: str | int | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize a create request without accepting executable capabilities."""
    if not isinstance(task, str) or not task.strip():
        raise McpPolicyError("missing_task", "task must be a non-empty research question")
    if len(task) > MAX_TASK_CHARS:
        raise McpPolicyError("task_too_large", f"task exceeds {MAX_TASK_CHARS} characters")
    scope = validate_task_scope(task)
    if not scope["allowed"]:
        raise McpPolicyError("policy_scope_blocked", f"task contains blocked action terms: {scope['violations']}")
    if mode not in MODES:
        raise McpPolicyError("invalid_mode", f"mode must be one of {sorted(MODES)}")
    if output_level not in OUTPUT_LEVELS:
        raise McpPolicyError("invalid_output_level", f"output_level must be one of {sorted(OUTPUT_LEVELS)}")
    if mode in {"backtest", "portfolio_research"} and output_level not in {"research_grade", "portfolio_grade"}:
        raise McpPolicyError("insufficient_output_level", f"{mode} requires research_grade or portfolio_grade")
    normalized_universe = universe or []
    if not isinstance(normalized_universe, list) or len(normalized_universe) > MAX_UNIVERSE_ITEMS or any(not isinstance(item, str) or not item.strip() for item in normalized_universe):
        raise McpPolicyError("invalid_universe", "universe must be a list of non-empty asset identifiers")
    if target is not None and not isinstance(target, str):
        raise McpPolicyError("invalid_target", "target must be a string")
    if horizon is not None and not isinstance(horizon, (str, int)):
        raise McpPolicyError("invalid_horizon", "horizon must be a string or integer")
    normalized_constraints = constraints or {}
    if not isinstance(normalized_constraints, dict):
        raise McpPolicyError("invalid_constraints", "constraints must be a JSON object")
    if len(json.dumps(normalized_constraints, ensure_ascii=False, default=str)) > MAX_CONSTRAINT_BYTES:
        raise McpPolicyError("constraints_too_large", f"constraints exceed {MAX_CONSTRAINT_BYTES} bytes")
    return {
        "task": task.strip(),
        "mode": mode,
        "output_level": output_level,
        "universe": [item.strip() for item in normalized_universe],
        "target": target.strip() if isinstance(target, str) else target,
        "horizon": horizon,
        "constraints": normalized_constraints,
    }
