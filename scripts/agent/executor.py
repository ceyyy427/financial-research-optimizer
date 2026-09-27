"""Checkpointed, bounded Plan-DAG executor with retries and timeouts."""
import asyncio
import hashlib
import inspect
import json
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timezone
from pathlib import Path

from .policy_guard import guard_action
from .budget import BudgetManager


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


def _execute_node(plan, node, handler, authorized_context, budget_manager, base_backoff=0.2):
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
            bytes_downloaded = int(result.get("bytes_downloaded", 0))
            browser_contexts = int(result.get("browser_contexts", 0))
            artifact_count = len(artifacts) if isinstance(artifacts, list) else 0
            limits = node.get("budget", {})
            if network_requests > int(limits.get("max_network_requests", 10**9)) or artifact_count > int(limits.get("max_artifacts", 10**9)) or bytes_downloaded > int(limits.get("max_bytes_downloaded", 10**18)):
                return {"node_id": node_id, "status": "blocked", "attempt": attempt, "message": "node budget exceeded", "artifacts": artifacts, "provenance": result.get("provenance", {}), "failure_class": "budget"}
            reserved, violations = budget_manager.reserve(network_requests, bytes_downloaded, artifact_count, browser_contexts)
            if not reserved:
                return {"node_id": node_id, "status": "blocked", "attempt": attempt, "message": "global budget exceeded: " + "; ".join(violations), "artifacts": artifacts, "provenance": result.get("provenance", {}), "failure_class": "global_budget", "budget_violations": violations}
            item = {"node_id": node_id, "status": status, "attempt": attempt, "message": result.get("message", ""), "artifacts": artifacts, "provenance": result.get("provenance", {}), "network_requests": network_requests, "bytes_downloaded": bytes_downloaded, "browser_contexts": browser_contexts}
            for field in ("execution_mode", "failure_class", "fallback_used", "preflight", "completion_level", "missing_capabilities"):
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


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _environment_fingerprint():
    return _fingerprint({"python": sys.version, "platform": platform.platform()})


def _artifact_hashes(results):
    hashes = {}
    for item in results:
        for artifact in item.get("artifacts", []) if isinstance(item, dict) else []:
            path = Path(artifact)
            if path.exists() and path.is_file():
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                hashes[str(path)] = "sha256:" + digest.hexdigest()
    return hashes


def _atomic_write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _save_checkpoint(path, plan, statuses, results, budget):
    if not path:
        return
    attempts = {item.get("node_id"): item.get("attempt", 0) for item in results if isinstance(item, dict) and item.get("node_id")}
    completed = [item.get("node_id") for item in results if item.get("status") in TERMINAL_SUCCESS]
    _atomic_write_json(path, {
        "checkpoint_version": 2,
        "plan_id": plan["plan_id"],
        "plan_hash": _fingerprint(plan),
        "contract_hash": _fingerprint(plan.get("immutable_contract", {})),
        "environment_fingerprint": _environment_fingerprint(),
        "config_fingerprint": plan.get("immutable_contract", {}).get("config_fingerprint"),
        "updated_at": _now(),
        "statuses": statuses,
        "node_attempts": attempts,
        "artifacts_hashes": _artifact_hashes(results),
        "last_completed_node": completed[-1] if completed else None,
        "resume_policy": "safe",
        "results": results,
        "budget": budget.snapshot(),
    })


def execute_plan(plan, handlers=None, authorized_context=False, checkpoint_path=None, max_workers=4, resume=True, global_budget=None):
    """Execute independent ready nodes in parallel and persist state after each batch."""
    handlers = handlers or {}
    nodes = plan.get("nodes", [])
    _validate_dag(nodes)
    node_map = {node["id"]: node for node in nodes}
    statuses = {node_id: "pending" for node_id in node_map}
    results = []
    budget_manager = BudgetManager(global_budget or plan.get("immutable_contract", {}).get("global_budget", {}))
    if checkpoint_path and resume and Path(checkpoint_path).exists():
        saved = json.loads(Path(checkpoint_path).read_text(encoding="utf-8"))
        mismatches = []
        if saved.get("checkpoint_version") != 2:
            mismatches.append("checkpoint_version")
        if saved.get("plan_hash") != _fingerprint(plan):
            mismatches.append("plan_hash")
        if saved.get("contract_hash") != _fingerprint(plan.get("immutable_contract", {})):
            mismatches.append("contract_hash")
        if saved.get("environment_fingerprint") != _environment_fingerprint():
            mismatches.append("environment_fingerprint")
        if mismatches:
            raise ValueError("checkpoint cannot resume safely; mismatched " + ", ".join(mismatches))
        for node_id, status in saved.get("statuses", {}).items():
            if node_id in statuses and status in ALL_STATUSES:
                statuses[node_id] = "pending" if status in {"running", "retrying"} else status
        results.extend(saved.get("results", []))
    if not handlers and not results:
        results = [{"node_id": node["id"], "status": "warning", "attempt": 0, "message": "planning_only: no handler registry was supplied", "artifacts": [], "provenance": {}, "execution_mode": "planning_only"} for node in nodes]
        statuses = {node["id"]: "warning" for node in nodes}
        _save_checkpoint(checkpoint_path, plan, statuses, results, budget_manager)
        return {"plan_id": plan["plan_id"], "status": "planning_only", "execution_mode": "planning_only", "completion_level": "planning_only", "missing_capabilities": [], "results": results, "budget": budget_manager.snapshot()}

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
            futures = {node["id"]: pool.submit(_execute_node, plan, node, handlers.get(node["tool"]), authorized_context, budget_manager) for node in ready}
            batch = [future.result() for future in futures.values()]
        for item in batch:
            node_id = item["node_id"]
            statuses[node_id] = item["status"]
            results.append(item)
            if item["status"] in TERMINAL_FAILURE and node_map[node_id].get("allow_degraded"):
                statuses[node_id] = "fallback"
                item["status"] = "fallback"
        _save_checkpoint(checkpoint_path, plan, statuses, results, budget_manager)
    overall = "blocked" if any(item["status"] == "blocked" for item in results) else ("failed" if any(item["status"] == "failed" for item in results) else "completed")
    missing = sorted({cap for item in results for cap in item.get("missing_capabilities", []) if isinstance(item, dict) and isinstance(item.get("missing_capabilities", []), list)})
    completed_nodes = {item.get("node_id") for item in results if item.get("status") in TERMINAL_SUCCESS}
    completion_level = "full" if overall == "completed" else ("data_capture" if "data_capture" in completed_nodes else "blocked")
    return {"plan_id": plan["plan_id"], "status": overall, "execution_mode": "executed", "completion_level": completion_level, "missing_capabilities": missing, "results": results, "budget": budget_manager.snapshot(), "checkpoint_path": str(checkpoint_path) if checkpoint_path else None}


async def _invoke_async(handler, contract, node):
    """Run async handlers in the caller loop; isolate sync handlers in a worker."""
    if inspect.iscoroutinefunction(handler) or inspect.iscoroutinefunction(getattr(handler, "__call__", None)):
        return await handler(contract, node)
    result = await asyncio.to_thread(handler, contract, node)
    if inspect.isawaitable(result):
        return await result
    return result


async def _execute_node_async(plan, node, handler, authorized_context, budget_manager):
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
            result = await asyncio.wait_for(_invoke_async(handler, plan["immutable_contract"], node), timeout=timeout_seconds)
            result = result if isinstance(result, dict) else {"status": "passed", "message": str(result)}
            status = {"pass": "passed", "success": "passed", "completed": "passed"}.get(result.get("status", "passed"), result.get("status", "passed"))
            if status not in ALL_STATUSES | {"not_applicable", "skipped"}:
                status = "failed"
                result["message"] = f"unknown handler status: {result.get('status')}"
            artifacts = result.get("artifacts", [])
            network_requests = int(result.get("network_requests", 0))
            bytes_downloaded = int(result.get("bytes_downloaded", 0))
            browser_contexts = int(result.get("browser_contexts", 0))
            artifact_count = len(artifacts) if isinstance(artifacts, list) else 0
            limits = node.get("budget", {})
            if network_requests > int(limits.get("max_network_requests", 10**9)) or artifact_count > int(limits.get("max_artifacts", 10**9)) or bytes_downloaded > int(limits.get("max_bytes_downloaded", 10**18)):
                return {"node_id": node_id, "status": "blocked", "attempt": attempt, "message": "node budget exceeded", "artifacts": artifacts, "provenance": result.get("provenance", {}), "failure_class": "budget"}
            reserved, violations = budget_manager.reserve(network_requests, bytes_downloaded, artifact_count, browser_contexts)
            if not reserved:
                return {"node_id": node_id, "status": "blocked", "attempt": attempt, "message": "global budget exceeded: " + "; ".join(violations), "artifacts": artifacts, "provenance": result.get("provenance", {}), "failure_class": "global_budget", "budget_violations": violations}
            item = {"node_id": node_id, "status": status, "attempt": attempt, "message": result.get("message", ""), "artifacts": artifacts, "provenance": result.get("provenance", {}), "network_requests": network_requests, "bytes_downloaded": bytes_downloaded, "browser_contexts": browser_contexts}
            for field in ("execution_mode", "failure_class", "fallback_used", "preflight", "completion_level", "missing_capabilities"):
                if field in result:
                    item[field] = result[field]
            return item
        except asyncio.TimeoutError:
            last_message, failure_class = f"timeout after {timeout_seconds}s", "timeout"
        except Exception as exc:
            last_message, failure_class = str(exc), "handler_error"
        if attempt <= max_retries:
            await asyncio.sleep(min(0.2 * (2 ** (attempt - 1)), 5.0))
    return {"node_id": node_id, "status": "failed", "attempt": max_retries + 1, "message": last_message, "artifacts": [], "provenance": {}, "failure_class": failure_class}


async def execute_plan_async(plan, handlers=None, authorized_context=False, checkpoint_path=None, max_workers=4, resume=True, global_budget=None):
    """Native-async executor for browser/CDP handlers; sync APIs remain supported above."""
    handlers = handlers or {}
    nodes = plan.get("nodes", [])
    _validate_dag(nodes)
    node_map = {node["id"]: node for node in nodes}
    statuses = {node_id: "pending" for node_id in node_map}
    results = []
    budget_manager = BudgetManager(global_budget or plan.get("immutable_contract", {}).get("global_budget", {}))
    if checkpoint_path and resume and Path(checkpoint_path).exists():
        saved = json.loads(Path(checkpoint_path).read_text(encoding="utf-8"))
        mismatches = []
        if saved.get("checkpoint_version") != 2:
            mismatches.append("checkpoint_version")
        if saved.get("plan_hash") != _fingerprint(plan):
            mismatches.append("plan_hash")
        if saved.get("contract_hash") != _fingerprint(plan.get("immutable_contract", {})):
            mismatches.append("contract_hash")
        if saved.get("environment_fingerprint") != _environment_fingerprint():
            mismatches.append("environment_fingerprint")
        if mismatches:
            raise ValueError("checkpoint cannot resume safely; mismatched " + ", ".join(mismatches))
        for node_id, status in saved.get("statuses", {}).items():
            if node_id in statuses and status in ALL_STATUSES:
                statuses[node_id] = "pending" if status in {"running", "retrying"} else status
        results.extend(saved.get("results", []))
    if not handlers and not results:
        results = [{"node_id": node["id"], "status": "warning", "attempt": 0, "message": "planning_only: no handler registry was supplied", "artifacts": [], "provenance": {}, "execution_mode": "planning_only"} for node in nodes]
        statuses = {node["id"]: "warning" for node in nodes}
        _save_checkpoint(checkpoint_path, plan, statuses, results, budget_manager)
        return {"plan_id": plan["plan_id"], "status": "planning_only", "execution_mode": "planning_only", "completion_level": "planning_only", "missing_capabilities": [], "results": results, "budget": budget_manager.snapshot()}
    semaphore = asyncio.Semaphore(max(1, max_workers))

    async def run_node(node):
        async with semaphore:
            return await _execute_node_async(plan, node, handlers.get(node["tool"]), authorized_context, budget_manager)

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
        batch = await asyncio.gather(*(run_node(node) for node in ready))
        for item in batch:
            node_id = item["node_id"]
            statuses[node_id] = item["status"]
            results.append(item)
            if item["status"] in TERMINAL_FAILURE and node_map[node_id].get("allow_degraded"):
                statuses[node_id] = "fallback"
                item["status"] = "fallback"
        _save_checkpoint(checkpoint_path, plan, statuses, results, budget_manager)
    overall = "blocked" if any(item["status"] == "blocked" for item in results) else ("failed" if any(item["status"] == "failed" for item in results) else "completed")
    missing = sorted({cap for item in results for cap in item.get("missing_capabilities", []) if isinstance(item, dict) and isinstance(item.get("missing_capabilities", []), list)})
    completed_nodes = {item.get("node_id") for item in results if item.get("status") in TERMINAL_SUCCESS}
    completion_level = "full" if overall == "completed" else ("data_capture" if "data_capture" in completed_nodes else "blocked")
    return {"plan_id": plan["plan_id"], "status": overall, "execution_mode": "executed", "completion_level": completion_level, "missing_capabilities": missing, "results": results, "budget": budget_manager.snapshot(), "checkpoint_path": str(checkpoint_path) if checkpoint_path else None}
