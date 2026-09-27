"""Phase-one MCP service methods backed by the core runtime."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from financial_research.run_store import RunStore, RunStoreError
from financial_research.runtime import get_run_status as runtime_get_run_status
from financial_research.runtime import prepare_research, read_research_artifact as runtime_read_research_artifact, run_research

from .policy import McpPolicyError, validate_create_request


class ResearchMcpService:
    """Own run lifecycle and prevent MCP callers from reaching the filesystem."""

    def __init__(self, run_root: str | None = None, max_concurrent_runs: int = 2, execution_mode: str = "execution"):
        self.store = RunStore(run_root or os.environ.get("FRO_MCP_RUN_ROOT", "artifacts/runs"))
        self.max_concurrent_runs = max(1, int(max_concurrent_runs))
        self.execution_mode = execution_mode
        self._semaphore = asyncio.Semaphore(self.max_concurrent_runs)
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    async def create_research_run(self, **request: Any) -> dict[str, Any]:
        try:
            normalized = validate_create_request(**request)
            run_id = self.store.create(
                normalized["task"],
                normalized["mode"],
                normalized["output_level"],
                request=normalized,
            )
            prepared = prepare_research(**normalized, run_id=run_id, execution_mode=self.execution_mode)
            self.store.save_contract(run_id, {**prepared["contract"], "execution_mode": self.execution_mode})
            self.store.save_plan(run_id, prepared["plan"])
            self.store.update_status(run_id, status="accepted", stage="accepted", plan_id=prepared["plan"]["plan_id"], last_message="run accepted")
            task = asyncio.create_task(self._execute(run_id, normalized))
            self._tasks[run_id] = task
            task.add_done_callback(lambda _: self._tasks.pop(run_id, None))
            return {"run_id": run_id, "status": "accepted", "plan_id": prepared["plan"]["plan_id"], "artifact_base_uri": f"research://runs/{run_id}"}
        except McpPolicyError as exc:
            return exc.as_dict()
        except (ValueError, RunStoreError) as exc:
            return {"status": "blocked", "reason_code": "contract_rejected", "message": str(exc), "user_action_required": True}

    async def _execute(self, run_id: str, request: dict[str, Any]) -> None:
        async with self._semaphore:
            try:
                await run_research(
                    **request,
                    execution_mode=self.execution_mode,
                    run_id=run_id,
                    run_store=self.store,
                    run_root=str(self.store.root),
                )
            except Exception as exc:  # noqa: BLE001 - status must be observable to the host
                self.store.update_status(run_id, status="failed", stage="failed", last_message=str(exc), error={"type": type(exc).__name__, "message": str(exc)})

    async def get_run_status(self, run_id: str) -> dict[str, Any]:
        try:
            return runtime_get_run_status(self.store, run_id)
        except (RunStoreError, FileNotFoundError) as exc:
            return {"status": "blocked", "reason_code": "run_not_found", "message": str(exc), "user_action_required": True}

    async def read_research_artifact(self, run_id: str, artifact: str) -> dict[str, Any]:
        try:
            return runtime_read_research_artifact(self.store, run_id, artifact)
        except (RunStoreError, FileNotFoundError) as exc:
            return {"status": "blocked", "reason_code": "artifact_not_registered", "message": str(exc), "user_action_required": True}
