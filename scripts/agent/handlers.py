"""Default research handlers used by the public runtime.

Handlers deliberately distinguish executable work from a capability gap.  A
handler never returns a successful result merely because a node is present in
the plan; unavailable stages are blocked with an actionable explanation.
"""
import json
from pathlib import Path


def _blocked(node, message, **extra):
    return {
        "status": "blocked",
        "message": message,
        "artifacts": [],
        "execution_mode": "capability_gap",
        "provenance": {"execution_mode": "capability_gap", "node": node.get("id")},
        **extra,
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
            return _blocked(node, "preflight blocked: " + "; ".join(result.get("blocking_reasons", [])), preflight=result)
        return {"status": "passed", "message": f"preflight status: {result.get('status')}", "artifacts": [], "provenance": {"preflight": result}}
    except Exception as exc:
        return _blocked(node, f"preflight failed: {exc}")


def _data_capture(contract, node):
    if not contract.get("refresh_plan") and not contract.get("source_url"):
        return _blocked(node, "source_url or refresh_plan is required for data capture")
    return _blocked(node, "data capture requires an executable source adapter; use scripts/execute_online_refresh.py")


def _unimplemented(name):
    def handler(contract, node):
        return _blocked(node, f"{name} is not implemented by the bounded default runtime; supply a registered handler")
    return handler


HANDLERS = {
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
