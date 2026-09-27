from mcp_server.policy import McpPolicyError, validate_create_request


def test_policy_normalizes_create_request():
    request = validate_create_request(
        "Estimate a bounded 20-day excess return",
        "forecasting",
        "research_grade",
        universe=[" SPY "],
        target=" excess_return ",
        horizon="20d",
        constraints={"cutoff": "2026-09-26"},
    )
    assert request["universe"] == ["SPY"]
    assert request["target"] == "excess_return"


def test_policy_blocks_unbounded_or_unsafe_request():
    try:
        validate_create_request("place_order for SPY", "forecasting", "research_grade")
    except McpPolicyError as exc:
        assert exc.code == "policy_scope_blocked"
    else:
        raise AssertionError("transaction-like tasks must be blocked at the MCP boundary")
    try:
        validate_create_request("x", "backtest", "standard")
    except McpPolicyError as exc:
        assert exc.code == "insufficient_output_level"
    else:
        raise AssertionError("backtest must not run at standard output level")
