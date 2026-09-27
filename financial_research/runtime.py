"""Single internal runtime used by CLI, MCP, and future web adapters."""

from __future__ import annotations

from typing import Any

from .run_store import create_run_store
from .store_protocol import RunStoreProtocol

try:
    from scripts.agent.executor import execute_plan_async
    from scripts.agent.handlers import HANDLERS, validate_handlers
    from scripts.agent.planner import build_plan, create_research_contract
except ImportError:  # pragma: no cover - supports execution from scripts/
    from agent.executor import execute_plan_async
    from agent.handlers import HANDLERS, validate_handlers
    from agent.planner import build_plan, create_research_contract


def get_run_status(store: RunStoreProtocol, run_id: str) -> dict[str, Any]:
    """Read a persisted run through the core runtime boundary."""
    return store.status(run_id)


def read_research_artifact(store: RunStoreProtocol, run_id: str, artifact: str) -> dict[str, Any]:
    """Read a manifest-registered artifact through the core runtime boundary."""
    return store.artifact(run_id, artifact, include_content=True)


def prepare_research(
    task: str,
    mode: str = "forecasting",
    output_level: str = "research_grade",
    constraints: dict[str, Any] | None = None,
    universe: list[str] | None = None,
    target: str | None = None,
    horizon: str | int | None = None,
    handlers: dict[str, Any] | None = None,
    run_id: str | None = None,
    config_path: str | None = None,
    execute_sources: bool = False,
    execution_mode: str = "execution",
    global_budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the immutable contract and Plan DAG without executing it."""
    contract = create_research_contract(
        task,
        mode=mode,
        output_level=output_level,
        constraints=constraints,
        universe=universe,
        target=target,
        horizon=horizon,
    )
    if run_id:
        contract["run_id"] = run_id
    if config_path:
        contract["config_path"] = str(config_path)
    contract["execute_sources"] = bool(execute_sources)
    contract["execution_mode"] = execution_mode
    if global_budget is not None:
        contract["global_budget"] = global_budget
    plan = build_plan(contract)
    registry = HANDLERS if handlers is None else handlers
    return {"contract": contract, "plan": plan, "handler_validation": validate_handlers(plan, registry)}


async def run_research(
    task: str,
    mode: str = "forecasting",
    output_level: str = "research_grade",
    constraints: dict[str, Any] | None = None,
    universe: list[str] | None = None,
    target: str | None = None,
    horizon: str | int | None = None,
    handlers: dict[str, Any] | None = None,
    authorized_context: bool = False,
    config_path: str | None = None,
    execute_sources: bool = False,
    execution_mode: str = "execution",
    run_id: str | None = None,
    resume: bool = True,
    run_store: RunStoreProtocol | None = None,
    run_root: str = "artifacts/runs",
    checkpoint_path: str | None = None,
    max_workers: int = 4,
    global_budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one bounded research run and optionally persist its audit trail.

    This is the only execution entry point that adapters should call.  The
    MCP layer never invokes individual handlers or reads a filesystem path.
    """
    store = run_store
    if store is None and run_root:
        store = create_run_store(run_root)
    if store is not None and run_id is None:
        run_id = store.create(
            task,
            mode,
            output_level,
            request={"universe": universe or [], "target": target, "horizon": horizon, "constraints": constraints or {}},
        )
    prepared = prepare_research(
        task,
        mode=mode,
        output_level=output_level,
        constraints=constraints,
        universe=universe,
        target=target,
        horizon=horizon,
        handlers=handlers,
        run_id=run_id,
        config_path=config_path,
        execute_sources=execute_sources,
        execution_mode=execution_mode,
        global_budget=global_budget,
    )
    contract = prepared["contract"]
    plan = prepared["plan"]
    registry = HANDLERS if handlers is None else handlers
    handler_validation = validate_handlers(plan, registry)

    if store is not None and run_id is not None:
        store.save_contract(run_id, contract)
        store.save_plan(run_id, plan)
        store.update_status(run_id, status="running", stage="contract_resolution", plan_id=plan["plan_id"], last_message="execution started")
        if checkpoint_path is None:
            checkpoint_path = str(store.run_dir(run_id) / "checkpoint.json")

    execution = await execute_plan_async(
        plan,
        handlers=(registry if execution_mode == "execution" else {}),
        authorized_context=authorized_context,
        checkpoint_path=checkpoint_path,
        max_workers=max_workers,
        resume=resume,
        global_budget=global_budget,
        run_store=store,
        run_id=run_id,
    )
    execution["requested_execution_mode"] = execution_mode
    if store is not None and run_id is not None:
        store.save_execution(run_id, execution)
        all_artifacts = [artifact for result in execution.get("results", []) for artifact in result.get("artifacts", [])]
        store.register_artifacts(run_id, all_artifacts)
        fallback_used = any(item.get("status") == "fallback" or item.get("fallback_used") for item in execution.get("results", []))
        current = store.status(run_id)
        if current.get("status") == "cancelled":
            lifecycle = "cancelled"
        else:
            lifecycle = "planning_only" if execution.get("status") == "planning_only" else ("degraded" if execution.get("status") == "completed" and fallback_used else ("completed" if execution.get("status") == "completed" else execution.get("status", "failed")))
            store.update_status(run_id, status=lifecycle, stage="artifacts" if lifecycle == "completed" else lifecycle, last_message=f"run {lifecycle}")

    return {"run_id": run_id, "contract": contract, "plan": plan, "handler_validation": handler_validation, "execution": execution}


async def run(
    task,
    mode="forecasting",
    output_level="research_grade",
    constraints=None,
    universe=None,
    target=None,
    horizon=None,
    handlers=None,
    authorized_context=False,
    config_path=None,
    execute_sources=False,
    execution_mode="execution",
    **kwargs,
):
    """Backward-compatible alias for :func:`run_research`."""
    return await run_research(
        task,
        mode=mode,
        output_level=output_level,
        constraints=constraints,
        universe=universe,
        target=target,
        horizon=horizon,
        handlers=handlers,
        authorized_context=authorized_context,
        config_path=config_path,
        execute_sources=execute_sources,
        execution_mode=execution_mode,
        **kwargs,
    )
