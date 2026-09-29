"""MCP lifecycle tools backed by the core runtime and durable store."""

from __future__ import annotations

import asyncio
import os
import socket
import uuid
from typing import Any
from pathlib import Path

from financial_research.run_store import IdempotencyConflictError, RunStoreError, StateTransitionError, StoreBusyError, create_run_store
from financial_research.runtime import get_run_status as runtime_get_run_status
from financial_research.runtime import prepare_research, read_research_artifact as runtime_read_research_artifact, run_research
from financial_research.store_protocol import RunStoreProtocol

from .policy import McpPolicyError, validate_create_request
from scripts.adapters.status import adapter_status


def _blocked(code: str, message: str) -> dict[str, Any]:
    return {"status": "blocked", "reason_code": code, "message": message, "user_action_required": True}


class ResearchMcpService:
    """Own task lifecycle, leases, idempotency, and client/tenant isolation."""

    def __init__(self, run_root: str | None = None, max_concurrent_runs: int = 2, execution_mode: str = "execution", lease_ttl_seconds: int = 300, worker_id: str | None = None, admin: bool = False):
        self.store: RunStoreProtocol = create_run_store(run_root or os.environ.get("FRO_MCP_RUN_ROOT", "artifacts/runs"))
        self.max_concurrent_runs = max(1, int(max_concurrent_runs))
        self.execution_mode = execution_mode
        self.lease_ttl_seconds = max(5, int(lease_ttl_seconds))
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
        self.admin = admin
        self._semaphore = asyncio.Semaphore(self.max_concurrent_runs)
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self.store.recover_stale_runs()

    def _authorized(self, run_id: str, client_id: str | None, owner_id: str | None, tenant_id: str | None, admin: bool = False) -> bool:
        try:
            return self.store.authorize(run_id, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id, admin=admin or self.admin)
        except RunStoreError:
            return False

    def _spawn(self, run_id: str, request: dict[str, Any]) -> None:
        task = asyncio.create_task(self._execute(run_id, request))
        self._tasks[run_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(run_id, None))

    async def create_research_run(self, **request: Any) -> dict[str, Any]:
        try:
            normalized = validate_create_request(**request)
            metadata = {key: normalized.pop(key, None) for key in ("idempotency_key", "client_id", "owner_id", "tenant_id")}
            created = self.store.create_with_result(
                normalized["task"], normalized["mode"], normalized["output_level"], request=normalized, **metadata
            )
            run_id = created["run_id"]
            if created.get("reused"):
                if not self._authorized(run_id, metadata.get("client_id"), metadata.get("owner_id"), metadata.get("tenant_id")):
                    return _blocked("run_not_found", "run is not available")
                current = runtime_get_run_status(self.store, run_id)
                return {"run_id": run_id, "status": current.get("status", "accepted"), "plan_id": current.get("plan_id"), "status_uri": f"research://runs/{run_id}/status", "artifact_base_uri": f"research://runs/{run_id}", "reused": True}
            prepared = prepare_research(**normalized, run_id=run_id, execution_mode=self.execution_mode)
            self.store.save_contract(run_id, {**prepared["contract"], "execution_mode": self.execution_mode})
            self.store.save_plan(run_id, prepared["plan"])
            self.store.update_status(run_id, status="accepted", stage="accepted", plan_id=prepared["plan"]["plan_id"], last_message="run accepted")
            self._spawn(run_id, {**normalized, "client_id": metadata.get("client_id"), "tenant_id": metadata.get("tenant_id")})
            return {"run_id": run_id, "status": "accepted", "plan_id": prepared["plan"]["plan_id"], "status_uri": f"research://runs/{run_id}/status", "artifact_base_uri": f"research://runs/{run_id}", "reused": False}
        except McpPolicyError as exc:
            return exc.as_dict()
        except IdempotencyConflictError as exc:
            return _blocked("idempotency_conflict", str(exc))
        except (ValueError, RunStoreError) as exc:
            return _blocked(getattr(exc, "code", "contract_rejected"), str(exc))

    async def _heartbeat_loop(self, run_id: str) -> None:
        interval = max(1, self.lease_ttl_seconds // 3)
        while True:
            await asyncio.sleep(interval)
            try:
                self.store.heartbeat_lease(run_id, self.worker_id, self.lease_ttl_seconds)
            except RunStoreError:
                return

    async def _execute(self, run_id: str, request: dict[str, Any]) -> None:
        async with self._semaphore:
            heartbeat = None
            try:
                self.store.acquire_lease(run_id, self.worker_id, self.lease_ttl_seconds)
                heartbeat = asyncio.create_task(self._heartbeat_loop(run_id))
                request = {key: value for key, value in request.items() if key not in {"client_id", "owner_id", "tenant_id"}}
                await run_research(**request, execution_mode=self.execution_mode, run_id=run_id, run_store=self.store, run_root=str(self.store.root))
            except StoreBusyError:
                return
            except asyncio.CancelledError:
                try:
                    self.store.cancel(run_id)
                finally:
                    raise
            except Exception as exc:  # noqa: BLE001 - status must remain observable to the host
                try:
                    self.store.update_status(run_id, status="failed", stage="failed", last_message=str(exc), error={"type": type(exc).__name__, "message": str(exc)})
                except RunStoreError:
                    pass
            finally:
                if heartbeat:
                    heartbeat.cancel()
                try:
                    current = self.store.status(run_id)
                    if current.get("worker_id") == self.worker_id:
                        self.store.release_lease(run_id, self.worker_id)
                except RunStoreError:
                    pass

    async def get_run_status(self, run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        if not self._authorized(run_id, client_id, owner_id, tenant_id, admin):
            return _blocked("run_not_found", "run is not available")
        try:
            status = runtime_get_run_status(self.store, run_id)
            execution = status.get("execution") or {}
            results = execution.get("results") or []
            source_status = "unknown"
            if any(item.get("status") == "blocked" for item in results):
                source_status = "blocked"
            elif any(item.get("fallback_used") or item.get("status") == "fallback" for item in results):
                source_status = "degraded"
            elif results:
                source_status = "live_certified" if any((item.get("provenance") or {}).get("source_capability", {}).get("live_certified") for item in results) else "fresh"
            completed = status.get("progress", {}).get("completed", 0)
            total = status.get("progress", {}).get("total", 0)
            status.update({"progress": {"completed": completed, "total": total, "percent": round(100 * completed / max(1, total), 2)}, "source_status": source_status, "freshness_status": "fresh" if source_status in {"fresh", "live_certified"} else source_status, "next_action": "render_artifacts" if status.get("status") in {"completed", "degraded"} else "resolve_blockers" if source_status == "blocked" else "continue", "user_action_required": source_status == "blocked"})
            return status
        except (RunStoreError, FileNotFoundError):
            return _blocked("run_not_found", "run is not available")

    async def read_research_artifact(self, run_id: str, artifact: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        if not self._authorized(run_id, client_id, owner_id, tenant_id, admin):
            return _blocked("artifact_not_registered", "artifact is not available")
        try:
            return runtime_read_research_artifact(self.store, run_id, artifact)
        except (RunStoreError, FileNotFoundError):
            return _blocked("artifact_not_registered", "artifact is not available")

    async def cancel_research_run(self, run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        if not self._authorized(run_id, client_id, owner_id, tenant_id, admin):
            return _blocked("run_not_found", "run is not available")
        try:
            return self.store.cancel(run_id)
        except (RunStoreError, StateTransitionError) as exc:
            return _blocked(getattr(exc, "code", "cancel_failed"), str(exc))

    async def resume_research_run(self, run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        return await self._restart(run_id, client_id, owner_id, tenant_id, admin, allowed={"interrupted", "failed", "blocked"}, reason="resume")

    async def retry_research_run(self, run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        return await self._restart(run_id, client_id, owner_id, tenant_id, admin, allowed={"failed", "blocked"}, reason="retry")

    async def _restart(self, run_id: str, client_id: str | None, owner_id: str | None, tenant_id: str | None, admin: bool, allowed: set[str], reason: str) -> dict[str, Any]:
        if not self._authorized(run_id, client_id, owner_id, tenant_id, admin):
            return _blocked("run_not_found", "run is not available")
        try:
            current = self.store.status(run_id)
            if current.get("status") not in allowed:
                return _blocked("invalid_state_transition", f"{reason} is not allowed from {current.get('status')}")
            request = self.store.request(run_id)
            self.store.update_status(run_id, status="queued", stage="queued", last_message=f"run {reason} queued")
            self._spawn(run_id, {**request, "client_id": client_id, "owner_id": owner_id, "tenant_id": tenant_id})
            return {"run_id": run_id, "status": "queued", "status_uri": f"research://runs/{run_id}/status"}
        except RunStoreError as exc:
            return _blocked(getattr(exc, "code", "restart_failed"), str(exc))

    async def list_research_runs(self, status: str | None = None, mode: str | None = None, created_after: str | None = None, limit: int = 50, cursor: int = 0, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        try:
            return self.store.list_runs(status=status, mode=mode, created_after=created_after, limit=limit, cursor=cursor, client_id=client_id, owner_id=owner_id, tenant_id=tenant_id, admin=admin or self.admin)
        except RunStoreError as exc:
            return _blocked(getattr(exc, "code", "list_failed"), str(exc))

    async def preview_scenario(self, run_id: str, changes: dict[str, Any], client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        """Create a new, lineage-bound scenario through the Python runtime."""
        if not self._authorized(run_id, client_id, owner_id, tenant_id, admin):
            return _blocked("run_not_found", "run is not available")
        try:
            from scripts.scenario import preview_scenario
            return preview_scenario(self.store, run_id, changes)
        except Exception as exc:  # noqa: BLE001 - expose structured scenario failure
            return _blocked("SCENARIO_FAILED", str(exc))

    async def compare_models(self, run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        if not self._authorized(run_id, client_id, owner_id, tenant_id, admin):
            return _blocked("run_not_found", "run is not available")
        try:
            evaluation = self.store.read_json(run_id, "rolling_evaluation.json")
            return {"status": "completed", "run_id": run_id, "models": evaluation.get("models", []), "selected_model": evaluation.get("selected_model"), "selection_metric": evaluation.get("selection_metric"), "evidence_ref": "rolling_evaluation.json"}
        except RunStoreError as exc:
            return _blocked("MODEL_EVALUATION_NOT_FOUND", str(exc))

    async def explain_metric(self, run_id: str, metric_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        if not self._authorized(run_id, client_id, owner_id, tenant_id, admin):
            return _blocked("run_not_found", "run is not available")
        try:
            payload = self.store.read_json(run_id, "knowledge_explanations.json")
            claims = payload if isinstance(payload, list) else payload.get("claims", [])
            matches = [claim for claim in claims if claim.get("claim_id") == metric_id or claim.get("formula_id") == metric_id]
            try:
                learning = self.store.read_json(run_id, "learning_cards.json")
            except RunStoreError:
                learning = {"schema_version": "1.0", "card_count": 0, "cards": []}
            cards = learning.get("cards", []) if isinstance(learning, dict) else []
            matched_cards = [card for card in cards if card.get("card_id") == metric_id or card.get("formula_id") == metric_id or metric_id in card.get("knowledge_refs", [])]
            return {"status": "completed" if matches or matched_cards else "not_available", "run_id": run_id, "metric_id": metric_id, "claims": matches, "explanations": matches, "learning_cards": matched_cards, "evidence_refs": sorted({ref for item in matches + matched_cards for ref in item.get("evidence_refs", [])}), "calculation_refs": sorted({ref for item in matches + matched_cards for ref in item.get("calculation_refs", item.get("lineage_refs", []))}), "source_ids": sorted({ref for item in matches + matched_cards for ref in item.get("source_ids", [])}), "evidence_ref": "knowledge_explanations.json"}
        except RunStoreError as exc:
            return _blocked("EXPLANATION_NOT_FOUND", str(exc))

    async def get_formula(self, formula_id: str, run_id: str | None = None) -> dict[str, Any]:
        from scripts.knowledge.formula_registry import get_formula
        formula = get_formula(formula_id)
        if run_id:
            try:
                manifest = self.store.read_json(run_id, "formula_manifest.json")
                formula = next((item for item in manifest.get("formulas", []) if item.get("formula_id") == formula_id), formula)
            except RunStoreError:
                pass
        formula.setdefault("compiled_asset", None)
        formula.setdefault("mathml_asset", None)
        formula.setdefault("compiler", None)
        formula.setdefault("compiler_version", None)
        formula.setdefault("sha256", "")
        formula.setdefault("status", "not_attempted")
        formula.setdefault("alt_text", "公式不可用")
        return {"status": "completed" if formula.get("tex") else "not_available", "formula_id": formula_id, "formula": formula, "tex": formula.get("tex", ""), "compiled_asset": formula.get("compiled_asset"), "alt_text": formula.get("alt_text"), "variables": formula.get("variables", {}), "compiler": formula.get("compiler"), "compiler_version": formula.get("compiler_version"), "formula_hash": formula.get("sha256"), "render_status": formula.get("status")}

    async def get_provenance(self, run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        if not self._authorized(run_id, client_id, owner_id, tenant_id, admin):
            return _blocked("run_not_found", "run is not available")
        values = {}
        for name in ("manifest.json", "lineage.json", "provenance_manifest.json", "source_reconciliation.json", "knowledge_explanations.json", "learning_cards.json", "formula_manifest.json"):
            try:
                values[name] = self.store.read_json(run_id, name)
            except RunStoreError:
                continue
        claims = values.get("knowledge_explanations.json", [])
        claims = claims if isinstance(claims, list) else claims.get("claims", [])
        claim_links = []
        for claim in claims:
            claim_links.append({"claim_id": claim.get("claim_id"), "evidence_refs": claim.get("evidence_refs", []), "calculation_refs": claim.get("calculation_refs", []), "source_ids": claim.get("source_ids", []), "input_hash": claim.get("input_hash"), "formula_id": claim.get("formula_id"), "artifact": "knowledge_explanations.json"})
        return {"status": "completed" if values else "not_available", "run_id": run_id, "artifacts": values, "claim_links": claim_links}

    async def refresh_source(self, source_id: str, dataset_id: str | None = None) -> dict[str, Any]:
        """Return the governed refresh route; actual fetching remains adapter-owned."""
        capability = await self.get_source_capability(source_id, dataset_id)
        if capability.get("status") != "passed":
            return capability
        row = capability["source_capability"]
        return {"status": "accepted", "source_id": source_id, "dataset_id": dataset_id, "source_capability": row, "next_action": "run the declared adapter smoke/refresh through Python", "user_action_required": False}

    async def get_plan_progress(self, run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        return await self.get_run_status(run_id, client_id, owner_id, tenant_id, admin)

    async def get_source_capability(self, source_id: str, dataset_id: str | None = None) -> dict[str, Any]:
        """Return evidence-driven adapter maturity for MCP routing decisions."""
        registry = Path(os.environ.get("FRO_SOURCE_REGISTRY", "config/source_registry.yaml"))
        if not registry.exists():
            return _blocked("source_registry_missing", str(registry))
        report = adapter_status(registry)
        rows = [row for row in report["profiles"] if row["source_id"] == source_id and (dataset_id is None or row["dataset_id"] == dataset_id)]
        if not rows:
            return _blocked("source_not_found", f"unknown source/dataset: {source_id}/{dataset_id or '*'}")
        row = rows[0]
        return {"status": "passed", "source_capability": {key: value for key, value in row.items() if key not in {"implementation_status", "parser_status"}}, "counts": {key: value for key, value in report.items() if key.endswith("_count")}}
