"""Non-negotiable safety and research-scope policy checks."""

BLOCKED_TERMS = ("place_order", "submit_order", "trade", "buy", "sell", "captcha", "paywall", "bypass_access")


def validate_task_scope(task):
    text = str(task).lower()
    violations = [term for term in BLOCKED_TERMS if term in text]
    return {"allowed": not violations, "violations": violations}


def guard_action(action, authorized_context=False):
    """Reject prohibited browser/agent actions before an executor invokes a tool."""
    name = str(action.get("action", "")).lower() if isinstance(action, dict) else str(action).lower()
    scope = validate_task_scope(name)
    if not scope["allowed"]:
        return {"allowed": False, "reason": f"blocked action terms: {scope['violations']}"}
    if isinstance(action, dict) and action.get("requires_auth") and not authorized_context:
        return {"allowed": False, "reason": "authorized browser context is required and was not granted"}
    if isinstance(action, dict) and action.get("relaxes_constraints"):
        return {"allowed": False, "reason": "agent cannot relax research or portfolio constraints"}
    return {"allowed": True, "reason": "within read-only research policy"}
