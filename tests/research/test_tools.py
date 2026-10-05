from __future__ import annotations

from finahinking.quant.services import ALLOWED_TOOLS, QuantServiceGateway
from finahinking.research.contracts import FailureKind
from finahinking.research.tools import (
    ResearchToolGateway,
    ResearchToolName,
    ResearchToolRequest,
    ResearchToolStatus,
)


def test_allowlisted_research_tool_returns_provenance_and_is_idempotent() -> None:
    gateway = ResearchToolGateway()
    request = ResearchToolRequest(
        name=ResearchToolName.INSPECT_DATASET,
        args={"dataset_id": "fixture-prices"},
        run_id="run-tools",
    )

    first = gateway.execute(request)
    second = gateway.execute(request)

    assert first.status is ResearchToolStatus.SUCCEEDED
    assert first.provenance["gateway"] == "finahinking-research-v1"
    assert first.result == second.result
    assert first.request_digest == second.request_digest


def test_quant_allowlist_is_delegated_without_broadening_existing_gateway() -> None:
    quant = QuantServiceGateway()
    for tool_name in ALLOWED_TOOLS:
        if tool_name != "quant.inspect_run":
            quant.register(tool_name, lambda params, name=tool_name: {"tool": name, "ok": True})
    gateway = ResearchToolGateway(quant_gateway=quant)
    response = gateway.execute(
        ResearchToolRequest(
            name="quant.run_backtest",
            args={"fixture": "prices"},
            run_id="run-tools",
        )
    )
    assert response.status is ResearchToolStatus.SUCCEEDED
    assert response.result["ok"] is True


def test_unknown_and_unsafe_requests_are_rejected() -> None:
    gateway = ResearchToolGateway()
    cases = (
        ResearchToolRequest(name="quant.run_unknown", args={}, run_id="run-tools"),
        ResearchToolRequest(name="research.compute_factor", args={"formula": "eval(x)"}, run_id="run-tools"),
        ResearchToolRequest(name="research.inspect_dataset", args={"path": "/etc/passwd"}, run_id="run-tools"),
        ResearchToolRequest(name="research.inspect_dataset", args={"url": "file:///tmp/x"}, run_id="run-tools"),
        ResearchToolRequest(name="research.inspect_dataset", args={"query": "SELECT * FROM prices"}, run_id="run-tools"),
    )
    for request in cases:
        response = gateway.execute(request)
        assert response.status is ResearchToolStatus.REJECTED
        assert response.failure_kind is FailureKind.TOOL_REJECTED


def test_callable_and_oversized_args_are_rejected() -> None:
    gateway = ResearchToolGateway(max_args_bytes=64)
    callable_response = gateway.execute(
        ResearchToolRequest(name="research.compute_factor", args={"compute": lambda: 1}, run_id="run-tools")
    )
    oversized_response = gateway.execute(
        ResearchToolRequest(name="research.compute_factor", args={"factor_id": "x" * 100}, run_id="run-tools")
    )
    assert callable_response.failure_kind is FailureKind.TOOL_REJECTED
    assert oversized_response.failure_kind is FailureKind.TOOL_REJECTED


def test_run_ownership_is_required_for_inspection() -> None:
    gateway = ResearchToolGateway()
    response = gateway.execute(
        ResearchToolRequest(
            name="quant.inspect_run",
            args={"run_id": "other-run", "projection": "summary"},
            run_id="run-tools",
        )
    )
    assert response.status is ResearchToolStatus.REJECTED
    assert response.failure_kind is FailureKind.TOOL_REJECTED
