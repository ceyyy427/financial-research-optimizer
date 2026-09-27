"""SQLite state backend with WAL and the same public contract as JSON."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .run_store import IdempotencyConflictError, RunStore, RunStoreError, canonical_request_hash


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SqliteRunStore(RunStore):
    """Use SQLite for run metadata while retaining the safe artifact files."""

    def __init__(self, root: str = "artifacts/runs"):
        super().__init__(root)
        self.db_path = self.root / "runs.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS runs(
              run_id TEXT PRIMARY KEY, idempotency_key TEXT, request_hash TEXT NOT NULL,
              client_id TEXT, owner_id TEXT, tenant_id TEXT, task TEXT NOT NULL,
              mode TEXT NOT NULL, output_level TEXT NOT NULL, status TEXT NOT NULL,
              stage TEXT, progress_json TEXT, contract_json TEXT, plan_json TEXT,
              execution_json TEXT, worker_id TEXT, lease_until TEXT, heartbeat_at TEXT,
              attempt INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            DROP INDEX IF EXISTS idx_runs_idempotency;
            CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_idempotency ON runs(tenant_id, client_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
            CREATE TABLE IF NOT EXISTS run_events(
              event_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
              event_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS artifacts(
              run_id TEXT NOT NULL, name TEXT NOT NULL, path TEXT NOT NULL,
              artifact_uri TEXT NOT NULL, mime_type TEXT, size_bytes INTEGER,
              sha256 TEXT NOT NULL, created_at TEXT NOT NULL,
              PRIMARY KEY(run_id, name), FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS checkpoints(
              run_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, plan_hash TEXT NOT NULL,
              checkpoint_json TEXT NOT NULL, updated_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
            );
            """)

    def _event(self, run_id: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO run_events(run_id,event_type,payload_json,created_at) VALUES(?,?,?,?)", (run_id, event_type, json.dumps(payload, ensure_ascii=False, default=str), _now()))

    def create_with_result(self, task: str, mode: str, output_level: str, request: dict[str, Any] | None = None, run_id: str | None = None, **metadata: Any) -> dict[str, Any]:
        identity = metadata.get("client_id") or metadata.get("owner_id") or "anonymous"
        tenant_id = metadata.get("tenant_id")
        key = metadata.get("idempotency_key")
        request_hash = canonical_request_hash({**(request or {}), "task": task, "mode": mode, "output_level": output_level})
        if key:
            with self._connect() as db:
                rows = db.execute("SELECT run_id, request_hash, client_id, owner_id, tenant_id FROM runs WHERE idempotency_key=?", (key,)).fetchall()
                for row in rows:
                    row_identity = row["client_id"] or row["owner_id"] or "anonymous"
                    if row_identity == identity and row["tenant_id"] == tenant_id:
                        if row["request_hash"] != request_hash:
                            raise IdempotencyConflictError("idempotency key was reused with different request parameters")
                        return {"run_id": row["run_id"], "reused": True, "request_hash": request_hash}
        result = super().create_with_result(task, mode, output_level, request=request, run_id=run_id, **metadata)
        run = self.get(result["run_id"])
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO runs(run_id,idempotency_key,request_hash,client_id,owner_id,tenant_id,task,mode,output_level,status,stage,progress_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (result["run_id"], run.get("idempotency_key"), run.get("request_hash", request_hash), run.get("client_id"), run.get("owner_id"), run.get("tenant_id"), task, mode, output_level, "accepted", "accepted", json.dumps({"completed": 0, "total": 0}), run["created_at"], run["updated_at"]))
        self._event(result["run_id"], "created", run)
        return result

    def _sync_run(self, run_id: str) -> None:
        run = self.get(run_id)
        status = super().status(run_id)
        with self._connect() as db:
            db.execute("UPDATE runs SET status=?,stage=?,progress_json=?,contract_json=?,plan_json=?,execution_json=?,worker_id=?,lease_until=?,heartbeat_at=?,attempt=?,updated_at=? WHERE run_id=?", (status.get("status"), status.get("stage"), json.dumps(status.get("progress", {})), json.dumps(self.read_json(run_id, "contract.json"), ensure_ascii=False) if (self.run_dir(run_id) / "contract.json").exists() else None, json.dumps(self.read_json(run_id, "plan.json"), ensure_ascii=False) if (self.run_dir(run_id) / "plan.json").exists() else None, json.dumps(status.get("execution", {}), ensure_ascii=False), status.get("worker_id"), status.get("lease_until"), status.get("heartbeat_at"), status.get("attempt", 0), status.get("updated_at"), run_id))

    def save_contract(self, run_id: str, contract: dict[str, Any]) -> None:
        super().save_contract(run_id, contract)
        self.register_artifacts(run_id, ["contract.json"])
        self._sync_run(run_id)
        self._event(run_id, "contract_saved", {"run_id": run_id})

    def save_plan(self, run_id: str, plan: dict[str, Any]) -> None:
        super().save_plan(run_id, plan)
        self.register_artifacts(run_id, ["plan.json"])
        self._sync_run(run_id)
        self._event(run_id, "plan_saved", {"plan_id": plan.get("plan_id")})

    def save_execution(self, run_id: str, execution: dict[str, Any], attempt: int | None = None) -> None:
        super().save_execution(run_id, execution, attempt=attempt)
        self.register_artifacts(run_id, ["execution_latest.json" if (self.run_dir(run_id) / "execution_latest.json").exists() else "execution.json"])
        self._sync_run(run_id)
        self._event(run_id, "execution_saved", {"status": execution.get("status"), "attempt": attempt or execution.get("attempt", 1)})

    def update_status(self, run_id: str, **fields: Any) -> dict[str, Any]:
        status = super().update_status(run_id, **fields)
        self._sync_run(run_id)
        self._event(run_id, "status_changed", fields)
        return status

    def register_artifacts(self, run_id: str, artifacts: list[Any] | None = None) -> list[dict[str, Any]]:
        items = super().register_artifacts(run_id, artifacts)
        with self._connect() as db:
            for item in items:
                db.execute("INSERT OR REPLACE INTO artifacts(run_id,name,path,artifact_uri,mime_type,size_bytes,sha256,created_at) VALUES(?,?,?,?,?,?,?,?)", (run_id, item["name"], item["path"], item["artifact_uri"], item.get("mime_type"), item.get("size_bytes"), item["sha256"], item.get("created_at", _now())))
        return items

    def save_checkpoint(self, run_id: str, checkpoint: dict[str, Any]):
        path = super().save_checkpoint(run_id, checkpoint)
        self.register_artifacts(run_id, ["checkpoint.json"])
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO checkpoints(run_id,plan_id,plan_hash,checkpoint_json,updated_at) VALUES(?,?,?,?,?)", (run_id, checkpoint.get("plan_id", ""), checkpoint.get("plan_hash", ""), json.dumps(checkpoint, ensure_ascii=False), _now()))
        return path

    def load_checkpoint(self, run_id: str):
        with self._connect() as db:
            row = db.execute("SELECT checkpoint_json FROM checkpoints WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row["checkpoint_json"]) if row else super().load_checkpoint(run_id)

    def acquire_lease(self, run_id: str, worker_id: str, ttl_seconds: int = 300):
        result = super().acquire_lease(run_id, worker_id, ttl_seconds)
        self._sync_run(run_id)
        self._event(run_id, "lease_acquired", {"worker_id": worker_id, "lease_until": result.get("lease_until")})
        return result

    def heartbeat_lease(self, run_id: str, worker_id: str, ttl_seconds: int = 300):
        result = super().heartbeat_lease(run_id, worker_id, ttl_seconds)
        self._sync_run(run_id)
        self._event(run_id, "lease_heartbeat", {"worker_id": worker_id})
        return result

    def cancel(self, run_id: str):
        result = super().cancel(run_id)
        self._sync_run(run_id)
        self._event(run_id, "cancelled", {"run_id": run_id})
        return result

    def close(self) -> None:
        return None
