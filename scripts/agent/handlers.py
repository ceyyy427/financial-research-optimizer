"""Default research handlers used by the public runtime.

Handlers deliberately distinguish executable work from a capability gap.  A
handler never returns a successful result merely because a node is present in
the plan; unavailable stages are blocked with an actionable explanation.
"""
import json
from pathlib import Path


def _blocked(node, message, **extra):
    missing_capabilities = list(extra.pop("missing_capabilities", []))
    return {
        "status": "blocked",
        "message": message,
        "artifacts": [],
        "execution_mode": "capability_gap",
        "completion_level": extra.pop("completion_level", "blocked"),
        "missing_capabilities": missing_capabilities,
        "provenance": {"execution_mode": "capability_gap", "node": node.get("id")},
        **extra,
    }


def _resolve_contract(contract, node):
    missing = contract.get("needs_user_input", [])
    if missing:
        return _blocked(
            node,
            "research contract needs explicit input: " + ", ".join(missing),
            missing_capabilities=missing,
        )
    return {
        "status": "passed",
        "message": "research contract resolved",
        "artifacts": [],
        "execution_mode": "executed",
        "completion_level": "contract_resolved",
        "missing_capabilities": [],
        "provenance": {"resolution": contract.get("resolution", {})},
    }


def _discover_sources(contract, node):
    """Resolve a source plan when a registry and topic are available."""
    registry = contract.get("source_registry_path") or "config/source_registry.yaml"
    if not Path(registry).exists():
        return _blocked(node, f"source registry not found: {registry}")
    try:
        from ..source_router import SourceRouter
    except ImportError:  # installed/script execution
        from source_router import SourceRouter
    try:
        router = SourceRouter.from_file(registry)
        plan = router.resolve(
            contract.get("target", contract.get("task", "financial data")),
            universe=contract.get("universe", []),
            required_capabilities=contract.get("required_capabilities", []),
            required_fields=contract.get("required_fields", []),
            authorization_status=contract.get("authorization_status", "unknown"),
            require_executable=bool(contract.get("execute_sources", False)),
        )
        return {"status": "passed", "message": "source plan resolved", "artifacts": [], "provenance": {"source_plan": plan}}
    except Exception as exc:
        return _blocked(node, f"source routing failed: {exc}")


def _preflight(contract, node):
    """Run the same preflight contract used by the CLI when a config is supplied."""
    config_path = contract.get("config_path")
    if not config_path:
        return _blocked(node, "config_path is required for executable preflight")
    try:
        try:
            from ..run_preflight import run_preflight
        except ImportError:
            from run_preflight import run_preflight
        result = run_preflight(config_path)
        if result.get("status") == "blocked":
            return _blocked(node, "preflight blocked: " + "; ".join(result.get("blocking_reasons", [])), preflight=result, missing_capabilities=result.get("blocking_reasons", []))
        return {"status": "passed", "message": f"preflight status: {result.get('status')}", "artifacts": [], "completion_level": "preflight_passed", "missing_capabilities": [], "provenance": {"preflight": result}}
    except Exception as exc:
        return _blocked(node, f"preflight failed: {exc}")


def _data_capture(contract, node):
    constraints = contract.get("constraints", {})
    source_id = contract.get("source_id") or constraints.get("source_id")
    source_url = contract.get("source_url") or constraints.get("source_url")
    output_dir = contract.get("output_dir") or constraints.get("output_dir")
    if not contract.get("execute_sources"):
        return _blocked(node, "execution_mode is planning-only for data capture; set execute_sources=true with an explicit source contract", missing_capabilities=["source_capture_authorization"])
    if not source_id or not source_url or not output_dir:
        return _blocked(node, "source_id, source_url and output_dir are required for executable data capture", missing_capabilities=["source_id", "source_url", "output_dir"])
    try:
        try:
            from ..execute_online_refresh import execute_data_refresh
        except ImportError:
            from execute_online_refresh import execute_data_refresh
        result = execute_data_refresh(
            source_id,
            source_url,
            output_dir,
            params=constraints.get("source_params", {}),
            registry_path=constraints.get("registry_path", "config/source_registry.yaml"),
            allow_degraded=bool(constraints.get("allow_degraded_sources", False)),
            user_agent=constraints.get("user_agent"),
        )
        if result.get("status") != "passed":
            return _blocked(node, result.get("message", "data refresh failed"), missing_capabilities=[result.get("failure_class", "data_refresh")], refresh=result)
        return {
            "status": "passed",
            "message": result.get("message", "data snapshot captured"),
            "artifacts": [result.get("normalized_file")] if result.get("normalized_file") else [],
            "network_requests": result.get("network_requests", 0),
            "bytes_downloaded": result.get("bytes_downloaded", 0),
            "completion_level": "source_capture_only",
            "missing_capabilities": [],
            "provenance": {"refresh": result},
        }
    except Exception as exc:
        return _blocked(node, f"data capture failed: {exc}", missing_capabilities=["source_capture"])


def _unimplemented(name):
    def handler(contract, node):
        return _blocked(node, f"{name} is not implemented by the bounded default runtime; supply a registered handler", missing_capabilities=[name])
    return handler


HANDLERS = {
    "resolve_contract": _resolve_contract,
    "discover_sources": _discover_sources,
    "capture_data": _data_capture,
    "run_preflight": _preflight,
    "normalize_dataset": _unimplemented("normalize_dataset"),
    "audit_dataset": _unimplemented("audit_dataset"),
    "build_features": _unimplemented("build_features"),
    "run_models": _unimplemented("run_models"),
    "run_overfitting_diagnostics": _unimplemented("run_overfitting_diagnostics"),
    "run_portfolio_optimization": _unimplemented("run_portfolio_optimization"),
    "post_selection_stress_test": _unimplemented("post_selection_stress_test"),
    "render_artifacts": _unimplemented("render_artifacts"),
}


def validate_handlers(plan, handlers=None):
    registry = HANDLERS if handlers is None else handlers
    missing = sorted({node["tool"] for node in plan.get("nodes", []) if node["tool"] not in registry})
    return {"valid": not missing, "missing": missing, "registered": sorted(registry)}
