from agent.planner import build_plan, create_research_contract
from agent.replanner import replan
from agent.policy_guard import guard_action
from browser.network_capture import NetworkRecorder


def test_plan_has_bounded_dependencies_and_immutable_contract():
    contract = create_research_contract("forecast SPY volatility", universe=["SPY"], target="volatility", horizon="20d")
    plan = build_plan(contract)
    assert plan["immutable_contract"] == contract
    ids = {node["id"] for node in plan["nodes"]}
    assert all(dependency in ids for node in plan["nodes"] for dependency in node["depends_on"])
    assert all(node["max_retries"] >= 0 and node["timeout_seconds"] > 0 for node in plan["nodes"])


def test_replanner_uses_declared_fallback_and_guard_blocks_dangerous_actions():
    contract = create_research_contract("forecast SPY", universe=["SPY"], target="return", horizon="20d")
    plan = build_plan(contract)
    result = replan(plan, {"replan_count": 0, "results": [{"node_id": "data_capture", "status": "failed", "message": "timeout"}]})
    assert result["status"] == "fallback"
    assert result["next_action"] in {"switch_source", "use_cached_snapshot", "mark_degraded"}
    assert guard_action({"action": "place_order"})["allowed"] is False
    assert guard_action({"action": "open_authorized_source", "requires_auth": True})["allowed"] is False


def test_network_recorder_redacts_headers_and_hashes_body():
    recorder = NetworkRecorder("provider_x")
    record = recorder.record_response("r1", "https://example.test/data", "GET", 200, {"Cookie": "secret"}, {"content-type": "application/json", "Set-Cookie": "secret"}, b'{"x":1}', "https://example.test")
    assert record["body_hash"]
    assert "secret" not in str(record)
    assert record["source_id"] == "provider_x"
