from agent.planner import build_plan, create_research_contract
from agent.replanner import replan
from agent.policy_guard import guard_action
from browser.network_capture import NetworkClassifier, NetworkRecorder


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


def test_network_classifier_separates_data_tracking_and_static_requests():
    data = NetworkClassifier.classify("https://api.example.test/v1/series?page=2", response_headers={"content-type": "application/json"}, body=b'{"data": []}')
    tracking = NetworkClassifier.classify("https://analytics.example.test/collect", response_headers={"content-type": "image/gif"})
    static = NetworkClassifier.classify("https://example.test/assets/app.js", response_headers={"content-type": "application/javascript"})
    assert data["classification"] == "financial_data_api"
    assert data["is_data_request"] is True
    assert data["pagination"] is True
    assert tracking["is_tracking_request"] is True
    assert static["is_static_asset"] is True
