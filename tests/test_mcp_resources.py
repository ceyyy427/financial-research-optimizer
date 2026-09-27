import asyncio

from mcp_server.resources import parse_resource_uri
from mcp_server.tools import ResearchMcpService


def test_resource_uri_is_strict():
    assert parse_resource_uri("research://runs/run_20260927T000000Z_abc123/analysis") == ("run_20260927T000000Z_abc123", "analysis")
    for uri in ("file:///etc/passwd", "research://runs/../../etc/passwd", "research://runs/run_bad/../secret"):
        try:
            parse_resource_uri(uri)
        except Exception:
            continue
        raise AssertionError(f"unsafe URI accepted: {uri}")


def test_artifact_reads_are_manifest_bounded(tmp_path):
    async def scenario():
        service = ResearchMcpService(run_root=str(tmp_path), execution_mode="planning")
        created = await service.create_research_run(
            task="Describe a synthetic market dataset",
            mode="descriptive_analysis",
            output_level="standard",
            universe=["SPY"],
            target="excess_return",
            horizon="20d",
            constraints={"cutoff": "2026-09-26", "calendar": "XNYS"},
        )
        assert created["status"] == "accepted"
        assert created["status_uri"].endswith("/status")
        run_id = created["run_id"]
        await service._tasks[run_id]
        artifact = await service.read_research_artifact(run_id, "contract")
        assert artifact["registered"] is True
        (tmp_path / run_id / "secret.txt").write_text("should not be exposed", encoding="utf-8")
        unregistered = await service.read_research_artifact(run_id, "secret.txt")
        assert unregistered["reason_code"] == "artifact_not_registered"
        blocked = await service.read_research_artifact(run_id, "../../etc/passwd")
        assert blocked["reason_code"] == "artifact_not_registered"

    asyncio.run(scenario())


def test_mcp_lifecycle_controls_and_tenant_isolation(tmp_path):
    async def scenario():
        service = ResearchMcpService(run_root=str(tmp_path), execution_mode="planning", worker_id="test-worker")
        created = await service.create_research_run(
            task="Describe a synthetic market dataset",
            mode="descriptive_analysis",
            output_level="standard",
            client_id="client-a",
            tenant_id="tenant-a",
            idempotency_key="same-request",
        )
        assert created["status"] == "accepted"
        run_id = created["run_id"]
        assert (await service.get_run_status(run_id, client_id="client-b", tenant_id="tenant-a"))["reason_code"] == "run_not_found"
        assert (await service.get_run_status(run_id, client_id="client-a", tenant_id="tenant-a"))["run_id"] == run_id
        assert (await service.cancel_research_run(run_id, client_id="client-a", tenant_id="tenant-a"))["status"] == "cancelled"
        reused = await service.create_research_run(
            task="Describe a synthetic market dataset",
            mode="descriptive_analysis",
            output_level="standard",
            client_id="client-a",
            tenant_id="tenant-a",
            idempotency_key="same-request",
        )
        assert reused["reused"] is True
        listed = await service.list_research_runs(client_id="client-a", tenant_id="tenant-a")
        assert any(item["run_id"] == run_id for item in listed["runs"])

    asyncio.run(scenario())
