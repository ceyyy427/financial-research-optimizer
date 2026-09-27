"""Optional MCP server exposing the phase-one research workflow boundary."""

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
    ) -> dict[str, Any]:
        """Create an asynchronous research run and return its run_id and plan_id."""
        return await service.create_research_run(task=task, mode=mode, output_level=output_level, universe=universe, target=target, horizon=horizon, constraints=constraints)

    @mcp.tool()
    async def get_run_status(run_id: str) -> dict[str, Any]:
        """Read lifecycle, progress, stage, fallback, and execution status for a run."""
        return await service.get_run_status(run_id)

    @mcp.tool()
    async def read_research_artifact(run_id: str, artifact: str) -> dict[str, Any]:
        """Read one manifest-registered artifact by logical name or safe alias."""
        return await service.read_research_artifact(run_id, artifact)

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
