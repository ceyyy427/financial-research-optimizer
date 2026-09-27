import pytest


def test_optional_mcp_server_registers_phase_one_boundary():
    pytest.importorskip("mcp")
    from mcp.server import MCPServer

    from mcp_server.server import create_server

    server = create_server()
    assert isinstance(server, MCPServer)
    assert hasattr(server, "run")
