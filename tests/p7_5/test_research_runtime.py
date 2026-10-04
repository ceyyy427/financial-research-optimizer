from __future__ import annotations

import json
import sqlite3

import pytest

from finahinking.p7 import Principal, SQLiteP7Repository, apply_p7_migration
from finahinking.p7_5.research import LocalResearchService


def make_repository() -> SQLiteP7Repository:
    connection = sqlite3.connect(":memory:")
    apply_p7_migration(connection)
    repository = SQLiteP7Repository(connection)
    repository.create_principal(Principal("alice", "Alice"))
    repository.create_session("alice-session", "alice")
    return repository


def test_quant_runs_real_authored_sample_ols_and_persists_json_artifact(tmp_path) -> None:
    service = LocalResearchService(make_repository(), "alice-session", tmp_path)

    result = service.run_quant({"question": "How does the market relate to asset returns?"})

    assert result["node_id"]
    assert result["dataset"]["observation_count"] >= 40
    assert result["numeric_results"]["sample_count"] >= 40
    assert result["numeric_results"]["beta"] != 0
    assert result["numeric_results"]["beta_standard_error"] >= 0
    assert result["dataset"]["split"]["test_count"] > 0
    assert result["code_commit"]
    assert result["limitations"]
    assert result["artifact_path"]
    assert json.loads((tmp_path / f"{result['node_id']}.json").read_text()) == result
    assert service.get_artifact(result["node_id"])["node_id"] == result["node_id"]


def test_strategy_guided_and_advanced_modes_share_strategy_spec_and_complete_research(tmp_path) -> None:
    repository = make_repository()
    service = LocalResearchService(repository, "alice-session", tmp_path)

    guided = service.run_strategy({"mode": "guided", "idea": "moving average trend"})
    advanced = service.run_strategy(
        {
            "mode": "advanced",
            "idea": "moving average trend",
            "options": {"moving_average_window": 20, "fee_bps": 5.0, "slippage_bps": 5.0},
        }
    )

    assert guided["mode"] == "guided"
    assert advanced["mode"] == "advanced"
    assert guided["strategy_fingerprint"] == advanced["strategy_fingerprint"]
    for result in (guided, advanced):
        assert result["feature_fingerprint"]
        assert result["backtest_fingerprint"]
        assert result["oos_fingerprint"]
        assert result["paper_fingerprint"]
        assert result["compare_fingerprint"]
        assert result["learning_fingerprint"]
        assert result["strategy"]["reviewed"] is True
        assert result["backtest"]["fingerprint"] == result["backtest_fingerprint"]
        assert result["oos"]["fingerprint"] == result["oos_fingerprint"]
        assert result["paper"]["fingerprint"] == result["paper_fingerprint"]
        assert result["compare"]["fingerprint"] == result["compare_fingerprint"]
        assert result["code_commit"]
        assert result["limitations"]
        assert service.get_artifact(result["node_id"])["strategy_fingerprint"] == result["strategy_fingerprint"]
    assert repository.list_strategy_versions("alice-session")


def test_runtime_rejects_arbitrary_execution_and_invalid_modes(tmp_path) -> None:
    service = LocalResearchService(make_repository(), "alice-session", tmp_path)

    with pytest.raises(ValueError, match="unsupported option|mode"):
        service.run_strategy({"mode": "advanced", "options": {"code": "__import__('os').system('id')"}})
    with pytest.raises(ValueError, match="mode"):
        service.run_strategy({"mode": "expert", "idea": "moving average trend"})
