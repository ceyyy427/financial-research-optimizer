"""Safe, filesystem-backed storage for research runs.

The store is deliberately small and boring: it persists JSON contracts,
plans, execution summaries, and a manifest of files that are explicitly
registered by the runtime.  MCP reads through this boundary instead of
accepting arbitrary filesystem paths.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_ID_RE = re.compile(r"^run_[A-Za-z0-9][A-Za-z0-9_.-]{2,127}$")
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024

ALIASES = {
    "contract": "contract.json",
    "plan": "plan.json",
    "status": "status.json",
    "preflight": "preflight.json",
    "sources": "sources.json",
    "analysis": "analysis.json",
    "lineage": "lineage.json",
    "manifest": "manifest.json",
    "report_html": "financial_research_brief.html",
    "decision_table": "decision_table.csv",
    "decision_table.csv": "decision_table.csv",
    "decision_table_md": "decision_table.md",
    "browser_trace": "browser_trace.json",
    "trace": "browser_trace.json",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_default(value: Any) -> str:
    return str(value)


class RunStoreError(RuntimeError):
    """Raised when a run or artifact cannot be accessed safely."""


class RunStore:
    """Persist runs below one operator-owned root directory."""

    def __init__(self, root: str | os.PathLike[str] = "artifacts/runs"):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _validate_run_id(self, run_id: str) -> str:
        if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
            raise RunStoreError("invalid run_id")
        return run_id

    def run_dir(self, run_id: str) -> Path:
        run_id = self._validate_run_id(run_id)
        candidate = (self.root / run_id).resolve()
        if candidate.parent != self.root:
            raise RunStoreError("run path escaped store root")
        return candidate

    def exists(self, run_id: str) -> bool:
        return self.run_dir(run_id).is_dir()

    def create(self, task: str, mode: str, output_level: str, request: dict[str, Any] | None = None, run_id: str | None = None) -> str:
        with self._lock:
            run_id = run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:12]}"
            run_dir = self.run_dir(run_id)
            if run_dir.exists():
                raise RunStoreError(f"run already exists: {run_id}")
            run_dir.mkdir(parents=True)
            created = _now()
            self._atomic_write(run_dir / "run.json", {
                "run_id": run_id,
                "task": task,
                "mode": mode,
                "output_level": output_level,
                "created_at": created,
                "updated_at": created,
                "request": request or {},
            })
            self._atomic_write(run_dir / "status.json", {
                "run_id": run_id,
                "status": "accepted",
                "stage": "accepted",
                "progress": {"completed": 0, "total": 0},
                "completed_nodes": [],
                "blocked_nodes": [],
                "fallback_used": False,
                "last_message": "run accepted",
                "created_at": created,
                "updated_at": created,
            })
            self._atomic_write(run_dir / "manifest.json", {
                "run_id": run_id,
                "artifacts": [],
                "updated_at": created,
            })
            self.register_artifacts(run_id, ["run.json", "status.json"])
            return run_id

    def _atomic_write(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
        temporary.replace(path)

    def write_json(self, run_id: str, filename: str, payload: Any) -> Path:
        run_dir = self.run_dir(run_id)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", filename) or Path(filename).name != filename:
            raise RunStoreError("artifact filename must be a simple file name")
        run_dir.mkdir(parents=True, exist_ok=True)
        path = (run_dir / filename).resolve()
        if path.parent != run_dir:
            raise RunStoreError("artifact path escaped run directory")
        with self._lock:
            self._atomic_write(path, payload)
            return path

    def read_json(self, run_id: str, filename: str) -> dict[str, Any]:
        path = self._safe_file(run_id, filename)
        if not path.exists():
            raise RunStoreError(f"artifact not found: {filename}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RunStoreError(f"invalid JSON artifact: {filename}") from exc

    def save_contract(self, run_id: str, contract: dict[str, Any]) -> None:
        self.write_json(run_id, "contract.json", contract)
        self.register_artifacts(run_id, ["contract.json"])

    def save_plan(self, run_id: str, plan: dict[str, Any]) -> None:
        self.write_json(run_id, "plan.json", plan)
        self.register_artifacts(run_id, ["plan.json"])

    def save_execution(self, run_id: str, execution: dict[str, Any]) -> None:
        self.write_json(run_id, "execution.json", execution)
        self.register_artifacts(run_id, ["execution.json"])

    def update_status(self, run_id: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            current = self.read_json(run_id, "status.json") if self._safe_file(run_id, "status.json").exists() else {"run_id": run_id}
            current.update(fields)
            current["run_id"] = run_id
            current["updated_at"] = _now()
            self.write_json(run_id, "status.json", current)
            self.register_artifacts(run_id, ["status.json"])
            return current

    def register_artifacts(self, run_id: str, artifacts: list[Any] | None) -> list[dict[str, Any]]:
        """Register only existing files that resolve below this run directory."""
        run_dir = self.run_dir(run_id)
        manifest_path = run_dir / "manifest.json"
        manifest = self.read_json(run_id, "manifest.json") if manifest_path.exists() else {"run_id": run_id, "artifacts": []}
        registered = {item.get("name"): item for item in manifest.get("artifacts", []) if isinstance(item, dict)}
        for item in artifacts or []:
            raw = item.get("path") if isinstance(item, dict) else item
            if not isinstance(raw, str) or not raw:
                continue
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = run_dir / candidate
            try:
                candidate = candidate.resolve()
                candidate.relative_to(run_dir)
            except ValueError:
                continue
            if not candidate.is_file() or candidate.stat().st_size > MAX_ARTIFACT_BYTES:
                continue
            relative = candidate.relative_to(run_dir).as_posix()
            data = candidate.read_bytes()
            name = item.get("name", relative) if isinstance(item, dict) else relative
            registered[str(name)] = self._metadata(run_id, str(name), relative, data)
        manifest = {"run_id": run_id, "artifacts": sorted(registered.values(), key=lambda value: value.get("name", "")), "updated_at": _now()}
        self.write_json(run_id, "manifest.json", manifest)
        return manifest["artifacts"]

    def _safe_file(self, run_id: str, filename: str) -> Path:
        run_dir = self.run_dir(run_id)
        if not isinstance(filename, str) or Path(filename).name != filename or filename in {"", ".", ".."}:
            raise RunStoreError("artifact must be a registered file name")
        path = (run_dir / filename).resolve()
        try:
            path.relative_to(run_dir)
        except ValueError as exc:
            raise RunStoreError("artifact path escaped run directory") from exc
        return path

    def _metadata(self, run_id: str, name: str, relative: str, data: bytes) -> dict[str, Any]:
        return {
            "name": name,
            "artifact_uri": f"research://runs/{run_id}/{name}",
            "path": relative,
            "mime_type": mimetypes.guess_type(relative)[0] or "application/octet-stream",
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def status(self, run_id: str) -> dict[str, Any]:
        run = self.read_json(run_id, "run.json")
        current = self.read_json(run_id, "status.json")
        plan = self.read_json(run_id, "plan.json") if self._safe_file(run_id, "plan.json").exists() else {}
        execution = self.read_json(run_id, "execution.json") if self._safe_file(run_id, "execution.json").exists() else {}
        results = execution.get("results", []) if isinstance(execution, dict) else []
        completed = [item.get("node_id") for item in results if item.get("status") in {"passed", "warning", "fallback", "skipped", "not_applicable"}]
        blocked = [item.get("node_id") for item in results if item.get("status") in {"blocked", "failed"}]
        total = len(plan.get("nodes", []))
        execution_status = execution.get("status")
        if execution_status in {"completed", "planning_only"}:
            lifecycle = "completed"
        elif execution_status == "blocked":
            lifecycle = "blocked"
        elif execution_status == "failed":
            lifecycle = "failed"
        else:
            lifecycle = current.get("status", "accepted")
        return {
            "run_id": run_id,
            "status": lifecycle,
            "stage": completed[-1] if completed else current.get("stage", "accepted"),
            "progress": {"completed": len(completed), "total": total},
            "completed_nodes": completed,
            "blocked_nodes": blocked,
            "fallback_used": any(item.get("status") == "fallback" or item.get("fallback_used") for item in results),
            "last_message": (results[-1].get("message") if results else current.get("last_message", "")),
            "plan_id": plan.get("plan_id") or execution.get("plan_id"),
            "mode": run.get("mode"),
            "output_level": run.get("output_level"),
            "created_at": run.get("created_at"),
            "updated_at": current.get("updated_at"),
            "completion_level": execution.get("completion_level"),
            "execution": execution,
        }

    def artifact(self, run_id: str, name: str, include_content: bool = True) -> dict[str, Any]:
        """Return metadata/content only for allow-listed or manifest-registered files."""
        run_dir = self.run_dir(run_id)
        self.read_json(run_id, "run.json")  # fail closed for unknown runs
        requested = str(name)
        filename = ALIASES.get(requested, requested)
        manifest = self.read_json(run_id, "manifest.json") if (run_dir / "manifest.json").exists() else {"artifacts": []}
        registered = {item.get("name"): item for item in manifest.get("artifacts", []) if isinstance(item, dict)}
        metadata = registered.get(requested) or registered.get(filename)
        path = self._safe_file(run_id, filename)
        if requested == "manifest" and path.is_file():
            data = path.read_bytes()
            result = self._metadata(run_id, requested, path.relative_to(run_dir).as_posix(), data)
            result["registered"] = True
            if include_content:
                result["content"] = data.decode("utf-8", errors="replace")
            return result
        if metadata is None:
            raise RunStoreError(f"artifact is not registered: {name}")
        if not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
            raise RunStoreError("artifact is unavailable or exceeds the read limit")
        data = path.read_bytes()
        result = self._metadata(run_id, requested, path.relative_to(run_dir).as_posix(), data)
        result["registered"] = metadata is not None
        if include_content and result["mime_type"].startswith(("text/", "application/json", "text/csv")):
            result["content"] = data.decode("utf-8", errors="replace")
        return result
