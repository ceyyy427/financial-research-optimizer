import pytest

from finahinking.quant.services import (
    ALLOWED_TOOLS,
    QuantServiceGateway,
    ToolRequest,
    ToolStatus,
)


def test_gateway_has_frozen_allowlist_and_rejects_unknown_or_executable_payload() -> None:
    assert set(ALLOWED_TOOLS) == {
        "quant.run_backtest",
        "quant.run_regression",
        "quant.evaluate_performance",
        "quant.analyze_risk",
        "quant.compare_benchmark",
        "quant.inspect_run",
    }
    gateway = QuantServiceGateway()
    rejected = gateway.execute(ToolRequest("quant.not_allowed", {}))
    assert rejected.status is ToolStatus.REJECTED
    with pytest.raises((TypeError, ValueError)):
        ToolRequest("quant.run_backtest", {"source_code": "__import__('os')"})


def test_tool_request_is_json_safe_and_defensive() -> None:
    payload = {"dataset_id": "fixture", "parameters": {"fee_bps": 5}}
    request = ToolRequest("quant.inspect_run", payload)
    payload["parameters"]["fee_bps"] = 999
    assert request.parameters["parameters"]["fee_bps"] == 5
    assert request.request_id


@pytest.mark.parametrize(
    "payload",
    [
        {"import": "os"},
        {"path": "/tmp/data.csv"},
        {"source": "python3 -c 'print(1)'"},
        {"eval": "payload"},
        {"delete": "artifact"},
    ],
)
def test_gateway_rejects_imports_paths_and_mutation_directives(payload: dict[str, str]) -> None:
    with pytest.raises((TypeError, ValueError)):
        ToolRequest("quant.inspect_run", payload)


def test_gateway_sanitizes_unexpected_domain_exceptions() -> None:
    gateway = QuantServiceGateway()
    gateway.register("quant.run_backtest", lambda _: (_ for _ in ()).throw(Exception("secret traceback")))
    response = gateway.execute(ToolRequest("quant.run_backtest", {}))
    assert response.status is ToolStatus.FAILED
    assert response.message == "domain service failed"
    assert "secret traceback" not in response.message


def test_gateway_exposes_unavailable_status_for_isolated_adapters() -> None:
    assert ToolStatus.UNAVAILABLE.value == "UNAVAILABLE"
