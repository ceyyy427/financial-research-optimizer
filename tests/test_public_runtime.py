import asyncio

from financial_research import run


def test_public_run_interface_returns_plan_without_browser_or_network():
    result = asyncio.run(run("forecast SPY volatility", universe=["SPY"], target="volatility", horizon="20d"))
    assert result["contract"]["target"] == "volatility"
    assert result["plan"]["nodes"]
    assert result["execution"]["status"] == "blocked"
    assert result["execution"]["execution_mode"] == "executed"
    assert any(item.get("execution_mode") == "capability_gap" for item in result["execution"]["results"])
