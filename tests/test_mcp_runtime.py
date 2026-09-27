import asyncio
import json

from financial_research.runtime import run_research


def test_runtime_persists_auditable_run(tmp_path):
    async def scenario():
        result = await run_research(
            "Describe a synthetic market dataset",
            mode="descriptive_analysis",
            output_level="standard",
            universe=["SPY"],
            target="excess_return",
            horizon="20d",
            constraints={"cutoff": "2026-09-26", "calendar": "XNYS"},
            execution_mode="planning",
            run_root=str(tmp_path),
        )
        assert result["run_id"].startswith("run_")
        run_dir = tmp_path / result["run_id"]
        assert (run_dir / "contract.json").exists()
        assert (run_dir / "plan.json").exists()
        assert (run_dir / "execution.json").exists()
        status = json.loads((run_dir / "status.json").read_text(encoding="utf-8"))
        assert status["status"] == "planning_only"

    asyncio.run(scenario())
