"""Durable JSON run store with cross-process locking and recovery hooks."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:  # Unix/macOS path used by the local and CI deployments.
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback is below.
    fcntl = None


RUN_ID_RE = re.compile(r"^run_[A-Za-z0-9][A-Za-z0-9_.-]{2,127}$")
MAX_ARTIFACT_BYTES = 4 * 1024 * 1024
LOCK_TIMEOUT_SECONDS = 10.0
TERMINAL_STATES = {"completed", "degraded", "blocked", "failed", "cancelled", "planning_only"}
ALIASES = {
    "contract": "contract.json", "plan": "plan.json", "status": "status.json",
    "preflight": "preflight.json", "sources": "sources.json", "analysis": "analysis.json",
    "lineage": "lineage.json", "manifest": "manifest.json", "execution": "execution.json",
    "execution_latest": "execution_latest.json", "report_html": "financial_research_brief.html",
    "decision_table": "decision_table.csv", "decision_table.csv": "decision_table.csv",
    "decision_table_md": "decision_table.md", "browser_trace": "browser_trace.json", "trace": "browser_trace.json",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_default(value: Any) -> str:
    return str(value)


def canonical_request_hash(request: dict[str, Any]) -> str:
    payload = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RunStoreError(RuntimeError):
    """Base error for safe run-store operations."""


class StoreBusyError(RunStoreError):
    """Another process owns the store or run lock."""

    code = "store_busy"


class IdempotencyConflictError(RunStoreError):
    """An idempotency key was reused with a different request."""

    code = "idempotency_conflict"


class StateTransitionError(RunStoreError):
    """A caller attempted an invalid lifecycle transition."""

    code = "invalid_state_transition"


@contextmanager
def _file_lock(path: Path, timeout: float = LOCK_TIMEOUT_SECONDS) -> Iterator[None]:
    """Acquire an inter-process lock, failing explicitly instead of overwriting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    deadline = time.monotonic() + timeout
    try:
        if fcntl is not None:
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise StoreBusyError(f"lock timeout: {path}")
                    time.sleep(0.01)
        else:  # pragma: no cover - exercised only on platforms without fcntl.
            marker = path.with_suffix(path.suffix + ".owner")
            owner = False
            while not owner:
                try:
                    fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                    os.close(fd)
                    owner = True
                except FileExistsError:
                    if time.monotonic() >= deadline:
                        raise StoreBusyError(f"lock timeout: {path}")
                    time.sleep(0.01)
        yield
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        else:  # pragma: no cover
            marker = path.with_suffix(path.suffix + ".owner")
            try:
                marker.unlink()
            except FileNotFoundError:
                pass
        handle.close()


class RunStore:
    """Default JSON backend; its public surface is backend-compatible."""

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

    @contextmanager
    def _run_lock(self, run_id: str) -> Iterator[Path]:
        run_dir = self.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        with _file_lock(run_dir / ".run.lock"):
            yield run_dir

    def exists(self, run_id: str) -> bool:
        return self.run_dir(run_id).is_dir()

    def _read_json_unlocked(self, path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RunStoreError(f"invalid JSON artifact: {path.name}") from exc

    def _atomic_write(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Some filesystems do not permit directory fsync; the file itself
            # is still atomically replaced and fsynced.
            pass

    def _write_json_unlocked(self, run_dir: Path, filename: str, payload: Any) -> Path:
        relative = Path(filename)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise RunStoreError("artifact filename must stay below the run directory")
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in relative.parts):
            raise RunStoreError("artifact filename contains unsupported characters")
        path = (run_dir / relative).resolve()
        try:
            path.relative_to(run_dir)
        except ValueError:
            raise RunStoreError("artifact path escaped run directory")
        self._atomic_write(path, payload)
        return path

    def _index_path(self) -> Path:
        return self.root / "idempotency.json"

    def _load_index_unlocked(self) -> dict[str, Any]:
        if not self._index_path().exists():
            return {"version": 1, "items": {}}
        return self._read_json_unlocked(self._index_path())

    def _request_payload(self, task: str, mode: str, output_level: str, request: dict[str, Any] | None) -> dict[str, Any]:
        payload = dict(request or {})
        payload.update({"task": task, "mode": mode, "output_level": output_level})
        return payload

    def create_with_result(
        self,
        task: str,
        mode: str,
        output_level: str,
        request: dict[str, Any] | None = None,
        run_id: str | None = None,
        idempotency_key: str | None = None,
        client_id: str | None = None,
        owner_id: str | None = None,
        tenant_id: str | None = None,
    ) -> dict[str, Any]:
        request_payload = self._request_payload(task, mode, output_level, request)
        request_hash = canonical_request_hash(request_payload)
        identity = f"{tenant_id or 'default'}:{client_id or owner_id or 'anonymous'}:{idempotency_key}" if idempotency_key else None
        with _file_lock(self.root / ".store.lock"):
            index = self._load_index_unlocked()
            if identity and identity in index.get("items", {}):
                existing = index["items"][identity]
                if existing.get("request_hash") != request_hash:
                    raise IdempotencyConflictError("idempotency key was reused with different request parameters")
                return {"run_id": existing["run_id"], "reused": True, "request_hash": request_hash}
            run_id = run_id or f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:12]}"
            run_dir = self.run_dir(run_id)
            if run_dir.exists() and any(run_dir.iterdir()):
                raise RunStoreError(f"run already exists: {run_id}")
            run_dir.mkdir(parents=True, exist_ok=True)
            created = _now()
            self._atomic_write(run_dir / "run.json", {
                "run_id": run_id, "task": task, "mode": mode, "output_level": output_level,
                "idempotency_key": idempotency_key, "request_hash": request_hash,
                "client_id": client_id, "owner_id": owner_id or client_id, "tenant_id": tenant_id,
                "created_at": created, "updated_at": created, "request": request_payload,
            })
            self._atomic_write(run_dir / "status.json", {
                "run_id": run_id, "status": "accepted", "stage": "accepted",
                "progress": {"completed": 0, "total": 0}, "completed_nodes": [], "blocked_nodes": [],
                "fallback_used": False, "last_message": "run accepted", "attempt": 0,
                "created_at": created, "updated_at": created,
            })
            self._atomic_write(run_dir / "manifest.json", {"run_id": run_id, "artifacts": [], "updated_at": created})
            if identity:
                index.setdefault("items", {})[identity] = {"run_id": run_id, "request_hash": request_hash, "created_at": created}
                self._atomic_write(self._index_path(), index)
            with self._run_lock(run_id):
                self._register_artifacts_unlocked(run_dir, ["run.json", "status.json"])
            return {"run_id": run_id, "reused": False, "request_hash": request_hash}

    def create(self, task: str, mode: str, output_level: str, request: dict[str, Any] | None = None, run_id: str | None = None, **metadata: Any) -> str:
        return self.create_with_result(task, mode, output_level, request=request, run_id=run_id, **metadata)["run_id"]

    def get(self, run_id: str) -> dict[str, Any]:
        with self._run_lock(run_id) as run_dir:
            path = run_dir / "run.json"
            if not path.exists():
                raise RunStoreError(f"run not found: {run_id}")
            return self._read_json_unlocked(path)

    def request(self, run_id: str) -> dict[str, Any]:
        return self.get(run_id).get("request", {})

    def read_json(self, run_id: str, filename: str) -> dict[str, Any]:
        with self._run_lock(run_id) as run_dir:
            path = self._safe_file_unlocked(run_dir, filename)
            if not path.exists():
                raise RunStoreError(f"artifact not found: {filename}")
            return self._read_json_unlocked(path)

    def _safe_file_unlocked(self, run_dir: Path, filename: str) -> Path:
        if not isinstance(filename, str) or Path(filename).name != filename or filename in {"", ".", ".."}:
            raise RunStoreError("artifact must be a registered file name")
        path = (run_dir / filename).resolve()
        try:
            path.relative_to(run_dir)
        except ValueError as exc:
            raise RunStoreError("artifact path escaped run directory") from exc
        return path

    def _metadata(self, run_id: str, name: str, relative: str, data: bytes) -> dict[str, Any]:
        return {"name": name, "artifact_uri": f"research://runs/{run_id}/{name}", "path": relative,
                "mime_type": mimetypes.guess_type(relative)[0] or "application/octet-stream",
                "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "created_at": _now()}

    def _register_artifacts_unlocked(self, run_dir: Path, artifacts: list[Any] | None) -> list[dict[str, Any]]:
        run_id = run_dir.name
        manifest_path = run_dir / "manifest.json"
        manifest = self._read_json_unlocked(manifest_path) if manifest_path.exists() else {"run_id": run_id, "artifacts": []}
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
            name = item.get("name", relative) if isinstance(item, dict) else relative
            registered[str(name)] = self._metadata(run_id, str(name), relative, candidate.read_bytes())
        manifest = {"run_id": run_id, "artifacts": sorted(registered.values(), key=lambda value: value.get("name", "")), "updated_at": _now()}
        self._atomic_write(manifest_path, manifest)
        return manifest["artifacts"]

    def write_json(self, run_id: str, filename: str, payload: Any) -> Path:
        with self._run_lock(run_id) as run_dir:
            return self._write_json_unlocked(run_dir, filename, payload)

    def save_contract(self, run_id: str, contract: dict[str, Any]) -> None:
        with self._run_lock(run_id) as run_dir:
            self._write_json_unlocked(run_dir, "contract.json", contract)
            self._register_artifacts_unlocked(run_dir, ["contract.json"])

    def save_plan(self, run_id: str, plan: dict[str, Any]) -> None:
        with self._run_lock(run_id) as run_dir:
            self._write_json_unlocked(run_dir, "plan.json", plan)
            self._register_artifacts_unlocked(run_dir, ["plan.json"])

    def save_execution(self, run_id: str, execution: dict[str, Any], attempt: int | None = None) -> None:
        with self._run_lock(run_id) as run_dir:
            existing = run_dir / "execution.json"
            attempt = int(attempt or execution.get("attempt", 1))
            if existing.exists():
                attempts_dir = run_dir / "attempts"
                attempts_dir.mkdir(exist_ok=True)
                self._write_json_unlocked(attempts_dir.parent, f"attempts/attempt_{attempt}.json", execution)
                self._write_json_unlocked(run_dir, "execution_latest.json", execution)
                self._register_artifacts_unlocked(run_dir, ["execution_latest.json", f"attempts/attempt_{attempt}.json"])
            else:
                self._write_json_unlocked(run_dir, "execution.json", execution)
                self._register_artifacts_unlocked(run_dir, ["execution.json"])

    def save_checkpoint(self, run_id: str, checkpoint: dict[str, Any]) -> Path:
        with self._run_lock(run_id) as run_dir:
            path = self._write_json_unlocked(run_dir, "checkpoint.json", checkpoint)
            self._register_artifacts_unlocked(run_dir, ["checkpoint.json"])
            return path

    def load_checkpoint(self, run_id: str) -> dict[str, Any] | None:
        with self._run_lock(run_id) as run_dir:
            path = run_dir / "checkpoint.json"
            return self._read_json_unlocked(path) if path.exists() else None

    def _allowed_transition(self, current: str, new: str) -> bool:
        if current == new:
            return True
        allowed = {
            "accepted": {"queued", "running", "cancelled", "interrupted"},
            "queued": {"running", "cancelled", "interrupted"},
            "running": {"completed", "degraded", "blocked", "failed", "cancelled", "interrupted", "planning_only"},
            "interrupted": {"queued", "running", "cancelled", "failed"},
            "failed": {"queued", "running", "cancelled"},
            "blocked": {"queued", "cancelled"},
        }
        return new in allowed.get(current, set())

    def update_status(self, run_id: str, **fields: Any) -> dict[str, Any]:
        with self._run_lock(run_id) as run_dir:
            path = run_dir / "status.json"
            current = self._read_json_unlocked(path) if path.exists() else {"run_id": run_id, "status": "accepted"}
            new_status = fields.get("status", current.get("status", "accepted"))
            if not self._allowed_transition(current.get("status", "accepted"), new_status):
                raise StateTransitionError(f"cannot transition {current.get('status')} -> {new_status}")
            current.update(fields)
            current["run_id"] = run_id
            current["updated_at"] = _now()
            self._write_json_unlocked(run_dir, "status.json", current)
            self._register_artifacts_unlocked(run_dir, ["status.json"])
            return current

    def register_artifacts(self, run_id: str, artifacts: list[Any] | None = None) -> list[dict[str, Any]]:
        with self._run_lock(run_id) as run_dir:
            return self._register_artifacts_unlocked(run_dir, artifacts)

    def acquire_lease(self, run_id: str, worker_id: str, ttl_seconds: int = 300) -> dict[str, Any]:
        with self._run_lock(run_id) as run_dir:
            path = run_dir / "status.json"
            status = self._read_json_unlocked(path)
            current = status.get("status", "accepted")
            now = datetime.now(timezone.utc)
            lease_until = status.get("lease_until")
            expired = not lease_until or datetime.fromisoformat(lease_until.replace("Z", "+00:00")) <= now
            if current == "running" and not expired and status.get("worker_id") != worker_id:
                raise StoreBusyError(f"run lease is held by {status.get('worker_id')}")
            if current not in {"accepted", "queued", "interrupted"} and not (current == "running" and expired):
                raise StateTransitionError(f"run {run_id} is not leasable from {current}")
            status.update({"status": "running", "worker_id": worker_id, "lease_until": (now.timestamp() + ttl_seconds), "heartbeat_at": _now(), "attempt": int(status.get("attempt", 0)) + 1, "updated_at": _now()})
            status["lease_until"] = datetime.fromtimestamp(status["lease_until"], timezone.utc).isoformat().replace("+00:00", "Z")
            self._write_json_unlocked(run_dir, "status.json", status)
            self._register_artifacts_unlocked(run_dir, ["status.json"])
            return status

    def heartbeat_lease(self, run_id: str, worker_id: str, ttl_seconds: int = 300) -> dict[str, Any]:
        with self._run_lock(run_id) as run_dir:
            status = self._read_json_unlocked(run_dir / "status.json")
            if status.get("status") != "running" or status.get("worker_id") != worker_id:
                raise StoreBusyError("worker does not own the run lease")
            now = datetime.now(timezone.utc)
            status["heartbeat_at"] = _now()
            status["lease_until"] = datetime.fromtimestamp(now.timestamp() + ttl_seconds, timezone.utc).isoformat().replace("+00:00", "Z")
            status["updated_at"] = _now()
            self._write_json_unlocked(run_dir, "status.json", status)
            self._register_artifacts_unlocked(run_dir, ["status.json"])
            return status

    def release_lease(self, run_id: str, worker_id: str, status: str | None = None) -> dict[str, Any]:
        with self._run_lock(run_id) as run_dir:
            current = self._read_json_unlocked(run_dir / "status.json")
            if current.get("worker_id") not in {None, worker_id}:
                raise StoreBusyError("worker does not own the run lease")
            if status and not self._allowed_transition(current.get("status", "running"), status):
                raise StateTransitionError(f"cannot transition {current.get('status')} -> {status}")
            if status:
                current["status"] = status
            current.update({"worker_id": None, "lease_until": None, "heartbeat_at": _now(), "updated_at": _now()})
            self._write_json_unlocked(run_dir, "status.json", current)
            self._register_artifacts_unlocked(run_dir, ["status.json"])
            return current

    def recover_stale_runs(self) -> list[str]:
        recovered = []
        for directory in self.root.iterdir():
            if not directory.is_dir() or not RUN_ID_RE.fullmatch(directory.name) or not (directory / "status.json").exists():
                continue
            try:
                status = self.read_json(directory.name, "status.json")
                lease_until = status.get("lease_until")
                expired = lease_until and datetime.fromisoformat(lease_until.replace("Z", "+00:00")) <= datetime.now(timezone.utc)
                if status.get("status") == "running" and expired:
                    self.update_status(directory.name, status="interrupted", stage="interrupted", last_message="worker lease expired", worker_id=None, lease_until=None, recovery_reason="stale_lease")
                    recovered.append(directory.name)
            except RunStoreError:
                continue
        return recovered

    def cancel(self, run_id: str) -> dict[str, Any]:
        with self._run_lock(run_id) as run_dir:
            current = self._read_json_unlocked(run_dir / "status.json")
            if current.get("status") in TERMINAL_STATES:
                return current
            current.update({"status": "cancelled", "stage": "cancelled", "worker_id": None, "lease_until": None, "updated_at": _now(), "last_message": "run cancelled"})
            self._write_json_unlocked(run_dir, "status.json", current)
            self._register_artifacts_unlocked(run_dir, ["status.json"])
            return current

    def authorize(self, run_id: str, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> bool:
        if admin:
            return True
        run = self.get(run_id)
        owner = run.get("owner_id") or run.get("client_id")
        run_tenant = run.get("tenant_id")
        return (owner is None or (client_id or owner_id) == owner) and (run_tenant is None or tenant_id == run_tenant)

    def list_runs(self, status: str | None = None, mode: str | None = None, created_after: str | None = None, limit: int = 50, cursor: int = 0, client_id: str | None = None, owner_id: str | None = None, tenant_id: str | None = None, admin: bool = False) -> dict[str, Any]:
        items = []
        for directory in sorted(self.root.iterdir(), key=lambda item: item.name, reverse=True):
            if not directory.is_dir() or not RUN_ID_RE.fullmatch(directory.name) or not (directory / "run.json").exists():
                continue
            try:
                run = self.get(directory.name)
                if not self.authorize(directory.name, client_id, owner_id, tenant_id, admin):
                    continue
                if status or mode or created_after:
                    current = self.status(directory.name)
                    if status and current.get("status") != status: continue
                    if mode and run.get("mode") != mode: continue
                    if created_after and run.get("created_at", "") < created_after: continue
                items.append(self.status(directory.name))
            except RunStoreError:
                continue
        page = items[cursor:cursor + max(1, min(limit, 200))]
        next_cursor = cursor + len(page) if cursor + len(page) < len(items) else None
        return {"runs": page, "next_cursor": next_cursor}

    def status(self, run_id: str) -> dict[str, Any]:
        with self._run_lock(run_id) as run_dir:
            run = self._read_json_unlocked(run_dir / "run.json")
            current = self._read_json_unlocked(run_dir / "status.json")
            plan = self._read_json_unlocked(run_dir / "plan.json") if (run_dir / "plan.json").exists() else {}
            execution_path = run_dir / "execution_latest.json" if (run_dir / "execution_latest.json").exists() else run_dir / "execution.json"
            execution = self._read_json_unlocked(execution_path) if execution_path.exists() else {}
            results = execution.get("results", []) if isinstance(execution, dict) else []
            completed = [item.get("node_id") for item in results if item.get("status") in {"passed", "warning", "fallback", "skipped", "not_applicable"}]
            blocked = [item.get("node_id") for item in results if item.get("status") in {"blocked", "failed"}]
            fallback_used = any(item.get("status") == "fallback" or item.get("fallback_used") for item in results)
            execution_status = execution.get("status")
            if current.get("status") == "cancelled":
                lifecycle = "cancelled"
            else:
                lifecycle = "planning_only" if execution_status == "planning_only" else ("degraded" if execution_status == "completed" and fallback_used else ("completed" if execution_status == "completed" else execution_status or current.get("status", "accepted")))
            return {"schema_version": "1.0", "run_id": run_id, "status": lifecycle, "stage": completed[-1] if completed else current.get("stage", "accepted"), "progress": {"completed": len(completed), "total": len(plan.get("nodes", [])), "percent": round(100 * len(completed) / max(1, len(plan.get("nodes", []))), 2)}, "completed_nodes": completed, "blocked_nodes": blocked, "fallback_used": fallback_used, "last_message": (results[-1].get("message") if results else current.get("last_message", "")), "plan_id": plan.get("plan_id") or execution.get("plan_id"), "mode": run.get("mode"), "output_level": run.get("output_level"), "created_at": run.get("created_at"), "updated_at": current.get("updated_at"), "completion_level": execution.get("completion_level"), "worker_id": current.get("worker_id"), "lease_until": current.get("lease_until"), "heartbeat_at": current.get("heartbeat_at"), "attempt": current.get("attempt", 0), "owner_id": run.get("owner_id"), "tenant_id": run.get("tenant_id"), "reason_code": "RUN_BLOCKED" if blocked else None, "next_action": "resolve_blockers" if blocked else ("render_artifacts" if lifecycle in {"completed", "degraded"} else "continue"), "user_action_required": bool(blocked), "provenance": [], "artifacts": [], "execution": execution}

    def artifact(self, run_id: str, name: str, include_content: bool = True) -> dict[str, Any]:
        run_dir = self.run_dir(run_id)
        self.get(run_id)
        requested = str(name)
        filename = ALIASES.get(requested, requested)
        with self._run_lock(run_id) as locked_dir:
            manifest = self._read_json_unlocked(locked_dir / "manifest.json") if (locked_dir / "manifest.json").exists() else {"artifacts": []}
            registered = {item.get("name"): item for item in manifest.get("artifacts", []) if isinstance(item, dict)}
            path = self._safe_file_unlocked(locked_dir, filename)
            if requested == "manifest" and path.is_file():
                data = path.read_bytes()
                result = self._metadata(run_id, requested, path.relative_to(locked_dir).as_posix(), data)
                result["registered"] = True
            else:
                metadata = registered.get(requested) or registered.get(filename)
                if metadata is None:
                    raise RunStoreError(f"artifact is not registered: {name}")
                if not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
                    raise RunStoreError("artifact is unavailable or exceeds the read limit")
                data = path.read_bytes()
                result = self._metadata(run_id, requested, path.relative_to(locked_dir).as_posix(), data)
                result["registered"] = True
            if include_content and (result["mime_type"].startswith(("text/", "application/json", "text/csv")) or requested == "manifest"):
                result["content"] = data.decode("utf-8", errors="replace")
            return result


def create_run_store(root: str | os.PathLike[str] = "artifacts/runs", backend: str | None = None):
    """Select SQLite for v1 multi-client runs; JSON remains explicit compatibility mode."""
    selected = (backend or os.environ.get("FRO_RUN_STORE", "sqlite")).lower()
    if selected == "json":
        return RunStore(root)
    if selected == "sqlite":
        from .sqlite_run_store import SqliteRunStore
        return SqliteRunStore(root)
    raise RunStoreError(f"unsupported run store backend: {selected}")
