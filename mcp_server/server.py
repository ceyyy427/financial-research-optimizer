"""Optional MCP server exposing the auditable research workflow boundary."""

from __future__ import annotations

import argparse
from typing import Any

from .resources import read_resource_uri
from .tools import ResearchMcpService


class MCPUnavailable(RuntimeError):
    """Raised when the optional MCP SDK has not been installed."""


def _mcp_server_class():
    try:
        from mcp.server import MCPServer

        return MCPServer
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise MCPUnavailable("MCP support is optional; install with python3 -m pip install -e '.[mcp]'") from exc


def create_server(service: ResearchMcpService | None = None):
    """Create a bound MCPServer; importing this module remains SDK-optional."""
    MCPServer = _mcp_server_class()
    service = service or ResearchMcpService()
    mcp = MCPServer("Financial Research Optimizer", instructions="Use the research tools to create bounded, auditable runs. Read registered artifacts only.")

    @mcp.tool()
    async def create_research_run(
        task: str,
        mode: str = "forecasting",
        output_level: str = "research_grade",
        universe: list[str] | None = None,
        target: str | None = None,
        horizon: str | int | None = None,
        constraints: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        client_id: str | None = None,
        owner_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """Create an asynchronous research run and return its run_id and plan_id."""
        return await service.create_research_run(task=task, mode=mode, output_level=output_level, universe=universe, target=target, horizon=horizon, constraints=constraints, idempotency_key=idempotency_key, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def get_run_status(run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Read lifecycle, progress, stage, fallback, and execution status for a run."""
        return await service.get_run_status(run_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def read_research_artifact(run_id: str, artifact: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Read one manifest-registered artifact by logical name or safe alias."""
        return await service.read_research_artifact(run_id, artifact, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def cancel_research_run(run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Request cancellation of a queued or running run."""
        return await service.cancel_research_run(run_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def resume_research_run(run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Resume an interrupted, failed, or blocked run from its checkpoint."""
        return await service.resume_research_run(run_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def retry_research_run(run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Retry a failed or blocked run with its original contract."""
        return await service.retry_research_run(run_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def list_research_runs(
        status: str | None = None,
        mode: str | None = None,
        created_after: str | None = None,
        limit: int = 50,
        cursor: int = 0,
        client_id: str | None = None,
        owner_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        """List only runs visible to the requesting client and tenant."""
        return await service.list_research_runs(status=status, mode=mode, created_after=created_after, limit=limit, cursor=cursor, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def get_source_capability(source_id: str, dataset_id: str | None = None) -> dict[str, Any]:
        """Read evidence-driven source maturity before selecting a data route."""
        return await service.get_source_capability(source_id, dataset_id)

    @mcp.tool()
    async def preview_scenario(run_id: str, changes: dict[str, Any], client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Create a new scenario artifact through Python; never overwrite the base run."""
        return await service.preview_scenario(run_id, changes, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def compare_models(run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Read saved rolling model comparisons without recomputing in the client."""
        return await service.compare_models(run_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def explain_metric(run_id: str, metric_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Read evidence-bound explanations generated by the Python engine."""
        return await service.explain_metric(run_id, metric_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def get_formula(formula_id: str) -> dict[str, Any]:
        """Read a registered formula and its accessible interpretation."""
        return await service.get_formula(formula_id)

    @mcp.tool()
    async def get_provenance(run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Read registered provenance and lineage artifacts for a run."""
        return await service.get_provenance(run_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.tool()
    async def refresh_source(source_id: str, dataset_id: str | None = None) -> dict[str, Any]:
        """Resolve the governed source refresh route; adapters perform the fetch."""
        return await service.refresh_source(source_id, dataset_id)

    @mcp.tool()
    async def get_plan_progress(run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None) -> dict[str, Any]:
        """Read stage and progress for a run."""
        return await service.get_plan_progress(run_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id)

    @mcp.resource("research://runs/{run_id}/{artifact}")
    async def research_resource(run_id: str, artifact: str) -> str:
        """Expose a registered run artifact through a research:// URI."""
        return read_resource_uri(service.store, f"research://runs/{run_id}/{artifact}")

    return mcp


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    mcp = create_server()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
