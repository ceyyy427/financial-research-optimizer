import asyncio
import json

from mcp_server.tools import ResearchMcpService
from scripts.knowledge.explanation_engine import build_explanations
from scripts.tex.compile_formula import build_manifest
from scripts.ui.state import normalize_state


def test_ui_state_is_bounded_and_formula_manifest_is_explicit():
    state = normalize_state({"active_tab": "not-a-tab", "theme": "bad"}, run_id="run_ui_001")
    assert state["active_tab"] == "overview"
    assert state["theme"] == "system"
    manifest = build_manifest(__import__("pathlib").Path("formulas"), ["naive_last_value"])
    assert manifest["render_status"] == "not_attempted"
    assert manifest["formulas"][0]["formula_id"] == "naive_last_value"


def test_scenario_mcp_creates_new_hashable_artifacts(tmp_path):
    async def run():
        service = ResearchMcpService(run_root=str(tmp_path))
        store = service.store
        run_id = store.create("scenario test", "portfolio_research", "portfolio_grade")
        analysis = {"forecast": {"horizon": 1}, "portfolio_robustness": {"return_matrix": [[0.01, 0.0], [-0.01, 0.02]], "weights": {"A": 0.5, "B": 0.5}, "prior_weights": [0.5, 0.5], "transaction_cost_bps": 10}}
        store.write_json(run_id, "analysis.json", analysis)
        result = await service.preview_scenario(run_id, {"volatility_shock": 0.2, "transaction_cost_bps": 25})
        assert result["status"] == "completed"
        assert result["scenario_id"]
        assert result["result_hash"]
        assert all((tmp_path / run_id / name).exists() for name in result["artifacts"])
        assert store.read_json(run_id, "analysis.json") == analysis
    asyncio.run(run())
