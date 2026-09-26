"""Compose contract creation, Plan DAG construction, and bounded execution."""
try:
    from scripts.agent.executor import execute_plan
    from scripts.agent.planner import build_plan, create_research_contract
except ImportError:
    from agent.executor import execute_plan
    from agent.planner import build_plan, create_research_contract


async def run(task, mode="forecasting", output_level="research_grade", constraints=None, universe=None, target=None, horizon=None, handlers=None, authorized_context=False):
    contract = create_research_contract(task, mode=mode, output_level=output_level, constraints=constraints, universe=universe, target=target, horizon=horizon)
    plan = build_plan(contract)
    execution = execute_plan(plan, handlers=handlers, authorized_context=authorized_context)
    return {"contract": contract, "plan": plan, "execution": execution}
