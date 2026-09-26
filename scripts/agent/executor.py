"""Bounded plan executor that delegates work to registered Python handlers."""
from datetime import datetime, timezone

from .policy_guard import guard_action


def execute_plan(plan, handlers=None, authorized_context=False):
    handlers = handlers or {}
    results = []
    completed = set()
    for node in plan.get("nodes", []):
        missing = [dependency for dependency in node.get("depends_on", []) if dependency not in completed]
        if missing:
            results.append({"node_id": node["id"], "status": "blocked", "attempt": 1, "message": f"dependencies not complete: {missing}", "artifacts": [], "provenance": {"checked_at": datetime.now(timezone.utc).isoformat()}})
            break
        policy = guard_action({"action": node["tool"]}, authorized_context=authorized_context)
        if not policy["allowed"]:
            results.append({"node_id": node["id"], "status": "blocked", "attempt": 1, "message": policy["reason"], "artifacts": [], "provenance": {}})
            break
        handler = handlers.get(node["tool"])
        try:
            result = handler(plan["immutable_contract"], node) if handler else {"status": "warning", "message": "handler not registered; planning-only execution", "artifacts": []}
            status = result.get("status", "pass")
            item = {"node_id": node["id"], "status": status, "attempt": 1, "message": result.get("message", ""), "artifacts": result.get("artifacts", []), "provenance": result.get("provenance", {})}
            if status in {"pass", "warning", "fallback"}:
                completed.add(node["id"])
            results.append(item)
            if status in {"failed", "blocked"} and not node.get("allow_degraded"):
                break
        except Exception as exc:
            results.append({"node_id": node["id"], "status": "failed", "attempt": 1, "message": str(exc), "artifacts": [], "provenance": {}})
            if not node.get("allow_degraded"):
                break
    return {"plan_id": plan["plan_id"], "status": "blocked" if any(item["status"] == "blocked" for item in results) else ("failed" if any(item["status"] == "failed" for item in results) else "completed"), "results": results}
