"""Compose contract creation, Plan DAG construction, and bounded execution."""
try:
    from scripts.agent.executor import execute_plan_async
    from scripts.agent.handlers import HANDLERS, validate_handlers
    from scripts.agent.planner import build_plan, create_research_contract
except ImportError:
    from agent.executor import execute_plan_async
    from agent.handlers import HANDLERS, validate_handlers
    from agent.planner import build_plan, create_research_contract


async def run(task, mode="forecasting", output_level="research_grade", constraints=None, universe=None, target=None, horizon=None, handlers=None, authorized_context=False, config_path=None, execute_sources=False, execution_mode="execution"):
    contract = create_research_contract(task, mode=mode, output_level=output_level, constraints=constraints, universe=universe, target=target, horizon=horizon)
    if config_path:
        contract["config_path"] = str(config_path)
    contract["execute_sources"] = bool(execute_sources)
    contract["execution_mode"] = execution_mode
    plan = build_plan(contract)
    registry = HANDLERS if handlers is None else handlers
    handler_validation = validate_handlers(plan, registry)
    execution = await execute_plan_async(plan, handlers=(registry if execution_mode == "execution" else {}), authorized_context=authorized_context)
    execution["requested_execution_mode"] = execution_mode
    return {"contract": contract, "plan": plan, "handler_validation": handler_validation, "execution": execution}
