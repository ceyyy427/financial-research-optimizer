"""Compose contract creation, Plan DAG construction, and bounded execution."""
try:
    from scripts.agent.executor import execute_plan
    from scripts.agent.handlers import HANDLERS, validate_handlers
    from scripts.agent.planner import build_plan, create_research_contract
except ImportError:
    from agent.executor import execute_plan
    from agent.handlers import HANDLERS, validate_handlers
    from agent.planner import build_plan, create_research_contract


async def run(task, mode="forecasting", output_level="research_grade", constraints=None, universe=None, target=None, horizon=None, handlers=None, authorized_context=False, config_path=None, execute_sources=False):
    contract = create_research_contract(task, mode=mode, output_level=output_level, constraints=constraints, universe=universe, target=target, horizon=horizon)
    if config_path:
        contract["config_path"] = str(config_path)
    contract["execute_sources"] = bool(execute_sources)
    plan = build_plan(contract)
    registry = HANDLERS if handlers is None else handlers
    handler_validation = validate_handlers(plan, registry)
    execution = execute_plan(plan, handlers=registry, authorized_context=authorized_context)
    return {"contract": contract, "plan": plan, "handler_validation": handler_validation, "execution": execution}
