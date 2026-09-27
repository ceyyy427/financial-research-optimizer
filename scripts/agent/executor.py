"""Checkpointed, bounded Plan-DAG executor with retries and timeouts."""
import asyncio
import inspect
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timezone
from pathlib import Path

from .policy_guard import guard_action


TERMINAL_SUCCESS = {"passed", "warning", "fallback", "not_applicable", "skipped"}
TERMINAL_FAILURE = {"failed", "blocked", "cancelled"}
ALL_STATUSES = {"pending", "running", "passed", "warning", "fallback", "retrying", "failed", "blocked", "cancelled"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _validate_dag(nodes):
    node_ids = [node.get("id") for node in nodes]
    if any(not node_id for node_id in node_ids) or len(node_ids) != len(set(node_ids)):
        raise ValueError("plan nodes must have unique non-empty ids")
    known = set(node_ids)
    for node in nodes:
        missing = set(node.get("depends_on", [])) - known
        if missing:
            raise ValueError(f"node {node['id']} has unknown dependencies: {sorted(missing)}")
    indegree = {node_id: 0 for node_id in node_ids}
    edges = {node_id: [] for node_id in node_ids}
    for node in nodes:
        for dependency in node.get("depends_on", []):
            indegree[node["id"]] += 1
            edges[dependency].append(node["id"])
    queue = [node_id for node_id, value in indegree.items() if value == 0]
    visited = []
    while queue:
        current = queue.pop(0)
        visited.append(current)
        for child in edges[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(visited) != len(node_ids):
        raise ValueError("plan contains a dependency cycle")
    return visited


def _invoke(handler, contract, node):
    result = handler(contract, node)
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def _execute_node(plan, node, handler, authorized_context, budget_state, base_backoff=0.2):
    node_id = node["id"]
    policy = guard_action({"action": node["tool"]}, authorized_context=authorized_context)
    if not policy["allowed"]:
        return {"node_id": node_id, "status": "blocked", "attempt": 1, "message": policy["reason"], "artifacts": [], "provenance": {}, "failure_class": "policy"}
    if handler is None:
        return {"node_id": node_id, "status": "warning", "attempt": 0, "message": "handler not registered; planning_only execution; no work was claimed", "artifacts": [], "provenance": {}, "execution_mode": "planning_only"}
    max_retries = int(node.get("max_retries", 0))
    timeout_seconds = float(node.get("timeout_seconds", 300))
    last_message = ""
    failure_class = "handler_error"
    for attempt in range(1, max_retries + 2):
        try:
            pool = ThreadPoolExecutor(max_workers=1)
            future = pool.submit(_invoke, handler, plan["immutable_contract"], node)
            try:
                result = future.result(timeout=timeout_seconds)
            finally:
                # A timed-out Python thread cannot be force-killed safely.  Do
                # not wait for it here: the node is failed and the DAG can
                # checkpoint/fallback immediately.  Production adapters should
                # use their own HTTP/process timeout as the hard boundary.
                pool.shutdown(wait=False, cancel_futures=True)
            result = result if isinstance(result, dict) else {"status": "passed", "message": str(result)}
            status = {"pass": "passed", "success": "passed", "completed": "passed"}.get(result.get("status", "passed"), result.get("status", "passed"))
            if status not in ALL_STATUSES | {"not_applicable", "skipped"}:
                status = "failed"
                result["message"] = f"unknown handler status: {result.get('status')}"
            artifacts = result.get("artifacts", [])
            network_requests = int(result.get("network_requests", 0))
            artifact_count = len(artifacts) if isinstance(artifacts, list) else 0
            limits = node.get("budget", {})
            if network_requests > int(limits.get("max_network_requests", 10**9)) or artifact_count > int(limits.get("max_artifacts", 10**9)):
                return {"node_id": node_id, "status": "blocked", "attempt": attempt, "message": "node budget exceeded", "artifacts": artifacts, "provenance": result.get("provenance", {}), "failure_class": "budget"}
            budget_state["network_requests"] += network_requests
            budget_state["artifacts"] += artifact_count
            item = {"node_id": node_id, "status": status, "attempt": attempt, "message": result.get("message", ""), "artifacts": artifacts, "provenance": result.get("provenance", {}), "network_requests": network_requests}
            for field in ("execution_mode", "failure_class", "fallback_used", "preflight"):
                if field in result:
                    item[field] = result[field]
            return item
        except FutureTimeout:
            last_message = f"timeout after {timeout_seconds}s"
            failure_class = "timeout"
        except Exception as exc:
            last_message = str(exc)
            failure_class = "handler_error"
        if attempt <= max_retries:
            time.sleep(min(base_backoff * (2 ** (attempt - 1)), 5.0))
    return {"node_id": node_id, "status": "failed", "attempt": max_retries + 1, "message": last_message, "artifacts": [], "provenance": {}, "failure_class": failure_class}


def _save_checkpoint(path, plan_id, statuses, results):
    if not path:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"plan_id": plan_id, "updated_at": _now(), "statuses": statuses, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")


def execute_plan(plan, handlers=None, authorized_context=False, checkpoint_path=None, max_workers=4, resume=True):
    """Execute independent ready nodes in parallel and persist state after each batch."""
    handlers = handlers or {}
    nodes = plan.get("nodes", [])
    _validate_dag(nodes)
    node_map = {node["id"]: node for node in nodes}
    statuses = {node_id: "pending" for node_id in node_map}
    results = []
    if checkpoint_path and resume and Path(checkpoint_path).exists():
        saved = json.loads(Path(checkpoint_path).read_text(encoding="utf-8"))
        if saved.get("plan_id") == plan.get("plan_id"):
            for node_id, status in saved.get("statuses", {}).items():
                if node_id in statuses and status in ALL_STATUSES:
                    statuses[node_id] = "pending" if status in {"running", "retrying"} else status
            results.extend(saved.get("results", []))
    budget_state = {"network_requests": 0, "artifacts": sum(len(item.get("artifacts", [])) for item in results if isinstance(item, dict))}
    if not handlers and not results:
        results = [{"node_id": node["id"], "status": "warning", "attempt": 0, "message": "planning_only: no handler registry was supplied", "artifacts": [], "provenance": {}, "execution_mode": "planning_only"} for node in nodes]
        statuses = {node["id"]: "warning" for node in nodes}
        _save_checkpoint(checkpoint_path, plan["plan_id"], statuses, results)
        return {"plan_id": plan["plan_id"], "status": "planning_only", "execution_mode": "planning_only", "results": results}

    while True:
        ready = [node for node in nodes if statuses[node["id"]] == "pending" and all(statuses.get(dep) in TERMINAL_SUCCESS for dep in node.get("depends_on", []))]
        if not ready:
            unresolved = [node for node in nodes if statuses[node["id"]] == "pending"]
            for node in unresolved:
                statuses[node["id"]] = "blocked"
                results.append({"node_id": node["id"], "status": "blocked", "attempt": 0, "message": "dependencies failed or DAG could not progress", "artifacts": [], "provenance": {}, "failure_class": "dependency"})
            break
        for node in ready:
            statuses[node["id"]] = "running"
        with ThreadPoolExecutor(max_workers=max(1, min(max_workers, len(ready)))) as pool:
            futures = {node["id"]: pool.submit(_execute_node, plan, node, handlers.get(node["tool"]), authorized_context, budget_state) for node in ready}
            batch = [future.result() for future in futures.values()]
        for item in batch:
            node_id = item["node_id"]
            statuses[node_id] = item["status"]
            results.append(item)
            if item["status"] in TERMINAL_FAILURE and node_map[node_id].get("allow_degraded"):
                statuses[node_id] = "fallback"
                item["status"] = "fallback"
        _save_checkpoint(checkpoint_path, plan["plan_id"], statuses, results)
    overall = "blocked" if any(item["status"] == "blocked" for item in results) else ("failed" if any(item["status"] == "failed" for item in results) else "completed")
    return {"plan_id": plan["plan_id"], "status": overall, "execution_mode": "executed", "results": results, "budget": budget_state, "checkpoint_path": str(checkpoint_path) if checkpoint_path else None}
