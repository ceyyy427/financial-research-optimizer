"""Durable, digest-only queue for bounded research jobs.

The queue deliberately stores no task payload, prompt, provider object, or
credential.  A worker resolves the task from its local registry using the
stable ``task_ref`` and verifies the persisted task digest before execution.
SQLite is used as a small local transactional journal; the ``job_events``
table is append-only and contains only public identifiers and digests.
"""

from __future__ import annotations

import math
import re
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .contracts import AgentTask, stable_digest


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    RETRYABLE = "retryable"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXTERNAL_WAITING = "external_waiting"


_PUBLIC_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_SENSITIVE_REF = re.compile(r"(?:api[-_]?key|secret|token|password|credential|authorization|prompt|endpoint|raw_response)", re.IGNORECASE)
_TERMINAL = frozenset({JobStatus.FAILED.value, JobStatus.CANCELLED.value, JobStatus.COMPLETED.value})


class StaleLeaseError(ValueError):
    """A worker attempted to mutate a job after losing its lease."""


def _ref(value: str, name: str) -> str:
    if not isinstance(value, str) or not _PUBLIC_REF.fullmatch(value) or _SENSITIVE_REF.search(value):
        raise ValueError(f"{name} must be a stable public reference")
    return value


def _digest(value: str, name: str) -> str:
    return _ref(value, name)


@dataclass(frozen=True, slots=True)
class JobRecord:
    job_id: str
    task_ref: str
    task_digest: str
    idempotency_key: str
    status: JobStatus
    attempts: int
    max_attempts: int
    available_at: float
    created_at: float
    updated_at: float
    worker_id: str | None = None
    lease_until: float | None = None
    lease_token: str | None = None
    last_error_digest: str | None = None
    checkpoint_ref: str | None = None
    result_ref: str | None = None
    report_ref: str | None = None
    learning_ref: str | None = None
    ledger_ref: str | None = None
    cancel_requested: bool = False
    task_type: str = "research"


class JobQueue:
    """SQLite-backed append-only state machine for research jobs."""

    def __init__(
        self,
        path: str | Path,
        *,
        clock: Callable[[], float] | None = None,
        lease_seconds: float = 300.0,
        backoff_base_seconds: float = 5.0,
        backoff_max_seconds: float = 3600.0,
        max_attempts: int = 3,
    ) -> None:
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in (lease_seconds, backoff_base_seconds, backoff_max_seconds)) or lease_seconds <= 0 or backoff_base_seconds < 0 or backoff_max_seconds < 0:
            raise ValueError("queue timing limits are invalid")
        if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock or time.time
        self._tasks: dict[str, AgentTask] = {}
        self.lease_seconds = float(lease_seconds)
        self.backoff_base_seconds = float(backoff_base_seconds)
        self.backoff_max_seconds = float(backoff_max_seconds)
        self.max_attempts = int(max_attempts)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    task_ref TEXT NOT NULL,
                    task_digest TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    available_at REAL NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    worker_id TEXT,
                    lease_until REAL,
                    lease_token TEXT,
                    last_error_digest TEXT,
                    checkpoint_ref TEXT,
                    result_ref TEXT,
                    report_ref TEXT,
                    learning_ref TEXT,
                    ledger_ref TEXT,
                    cancel_requested INTEGER NOT NULL DEFAULT 0
                    ,task_type TEXT NOT NULL DEFAULT 'research'
                    ,task_timeout REAL NOT NULL DEFAULT 30.0
                );
                CREATE INDEX IF NOT EXISTS jobs_claim_idx ON jobs(status, available_at, created_at);
                CREATE TABLE IF NOT EXISTS external_dispatches (
                    envelope_digest TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    external_ref TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    result_digest TEXT NOT NULL DEFAULT '',
                    failure_kind TEXT,
                    output_digest TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS job_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    reason_digest TEXT,
                    worker_id TEXT,
                    attempt INTEGER,
                    lease_token_digest TEXT
                );
                CREATE TABLE IF NOT EXISTS stage_checkpoints (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    stage_ref TEXT NOT NULL,
                    result_ref TEXT,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    UNIQUE(job_id, stage_name)
                );
                CREATE INDEX IF NOT EXISTS stage_checkpoints_job_idx ON stage_checkpoints(job_id, sequence);
                """
            )
            event_columns = {row["name"] for row in db.execute("PRAGMA table_info(job_events)").fetchall()}
            if "attempt" not in event_columns:
                db.execute("ALTER TABLE job_events ADD COLUMN attempt INTEGER")
            if "lease_token_digest" not in event_columns:
                db.execute("ALTER TABLE job_events ADD COLUMN lease_token_digest TEXT")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)").fetchall()}
            if "lease_token" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN lease_token TEXT")
            if "task_type" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN task_type TEXT NOT NULL DEFAULT 'research'")
            if "task_timeout" not in columns:
                db.execute("ALTER TABLE jobs ADD COLUMN task_timeout REAL NOT NULL DEFAULT 30.0")
            # Backfill external jobs written before the durable dispatch table
            # existed. Only public task/idempotency digests are copied.
            old_external = db.execute(
                "SELECT task_digest, task_ref, idempotency_key, status FROM jobs WHERE task_type='external'"
            ).fetchall()
            for item in old_external:
                dispatch_status = JobStatus.EXTERNAL_WAITING.value if item["status"] in {JobStatus.QUEUED.value, JobStatus.EXTERNAL_WAITING.value} else item["status"]
                db.execute(
                    "INSERT OR IGNORE INTO external_dispatches(envelope_digest, task_id, external_ref, status) VALUES(?,?,?,?)",
                    (item["task_digest"], item["task_ref"], item["idempotency_key"], dispatch_status),
                )
                if item["status"] == JobStatus.QUEUED.value:
                    db.execute("UPDATE jobs SET status=? WHERE task_digest=? AND task_type='external'", (JobStatus.EXTERNAL_WAITING.value, item["task_digest"]))

    @staticmethod
    def _task_digest(task: AgentTask) -> str:
        if not isinstance(task, AgentTask):
            raise TypeError("task must be AgentTask")
        # ``input_digest`` is the caller-owned digest of the input payload;
        # task.inputs are intentionally not serialized by this queue.
        return stable_digest(
            {
                "role": task.role,
                "task_id": task.task_id,
                "input_digest": task.input_digest,
                "capabilities": task.capabilities,
                "required": task.required,
                "timeout_seconds": task.timeout_seconds,
                "payload_digest": stable_digest(task.inputs),
            }
        )

    @staticmethod
    def _job_id(task_digest: str, idempotency_key: str) -> str:
        return f"job-{stable_digest({'task': task_digest, 'idempotency': idempotency_key})[:32]}"

    def enqueue(self, task: AgentTask, idempotency_key: str) -> JobRecord:
        if not isinstance(task, AgentTask):
            raise TypeError("task must be AgentTask")
        idempotency_key = _ref(idempotency_key, "idempotency_key")
        task_digest = self._task_digest(task)
        _ref(task.task_id, "task_ref")
        previous = self._tasks.get(task.task_id)
        if previous is not None and self._task_digest(previous) != task_digest:
            raise ValueError("task_id is already bound to another task digest")
        job_id = self._job_id(task_digest, idempotency_key)
        now = float(self._clock())
        with self._connect() as db:
            existing = db.execute("SELECT * FROM jobs WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
            if existing is not None:
                if existing["task_digest"] != task_digest:
                    raise ValueError("idempotency key is already bound to another task")
                result = self._row(existing)
            else:
                collision = db.execute(
                    "SELECT 1 FROM jobs WHERE task_ref = ? AND task_digest <> ? LIMIT 1",
                    (task.task_id, task_digest),
                ).fetchone()
                if collision is not None:
                    raise ValueError("task_id is already bound to another persisted task digest")
                db.execute(
                    """INSERT INTO jobs
                    (job_id, task_ref, task_digest, idempotency_key, status, attempts,
                     max_attempts, available_at, created_at, updated_at, task_timeout)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)""",
                    (job_id, task.task_id, task_digest, idempotency_key, JobStatus.QUEUED.value, self.max_attempts, now, now, now, float(task.timeout_seconds)),
                )
                self._event(db, job_id, JobStatus.QUEUED.value, now)
                row = db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
                assert row is not None
                result = self._row(row)
        # Register only after all durable identity checks and the transaction
        # succeed; rejected collisions must not overwrite the resolver.
        self._tasks[task.task_id] = task
        return result

    def enqueue_external(self, envelope: object, idempotency_key: str | None = None) -> JobRecord:
        """Queue a Codex handoff while retaining only public digests."""
        task_id = getattr(envelope, "task_id", None)
        to_dict = getattr(envelope, "to_dict", None)
        if not isinstance(task_id, str) or not callable(to_dict):
            raise TypeError("external envelope must expose task_id and to_dict")
        payload = to_dict()
        task_digest = stable_digest(payload)
        key = idempotency_key or f"external:{task_digest[:32]}"
        key = _ref(key, "idempotency_key")
        job_id = self._job_id(task_digest, key)
        now = float(self._clock())
        with self._connect() as db:
            existing = db.execute("SELECT * FROM jobs WHERE idempotency_key = ?", (key,)).fetchone()
            if existing is not None:
                if existing["task_digest"] != task_digest:
                    raise ValueError("idempotency key is already bound to another task")
                return self._row(existing)
            collision = db.execute("SELECT 1 FROM jobs WHERE task_ref = ? AND task_digest <> ? LIMIT 1", (task_id, task_digest)).fetchone()
            if collision is not None:
                raise ValueError("task_id is already bound to another persisted task digest")
            db.execute(
                """INSERT INTO jobs (job_id, task_ref, task_digest, idempotency_key, status, attempts, max_attempts, available_at, created_at, updated_at, task_type)
                   VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, 'external')""",
                (job_id, _ref(task_id, "task_ref"), task_digest, key, JobStatus.EXTERNAL_WAITING.value, self.max_attempts, now, now, now),
            )
            self._event(db, job_id, JobStatus.EXTERNAL_WAITING.value, now)
            db.execute("INSERT OR IGNORE INTO external_dispatches(envelope_digest, task_id, external_ref, status) VALUES(?,?,?,?)", (task_digest, task_id, key, JobStatus.EXTERNAL_WAITING.value))
            row = self._must_row(db, job_id)
            db.commit()
            return self._row(row)

    def external_dispatch(self, envelope_digest: str) -> dict[str, str] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM external_dispatches WHERE envelope_digest=?", (envelope_digest,)).fetchone()
            return None if row is None else dict(zip(row.keys(), row))

    def record_external_result(self, envelope_digest: str, *, status: str, result_digest: str, failure_kind: str | None, output_digest: str) -> None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM external_dispatches WHERE envelope_digest=?", (envelope_digest,)).fetchone()
            if row is None:
                raise KeyError("unknown external dispatch")
            if row["status"] not in {JobStatus.EXTERNAL_WAITING.value, JobStatus.QUEUED.value}:
                return
            db.execute("UPDATE external_dispatches SET status=?, result_digest=?, failure_kind=?, output_digest=? WHERE envelope_digest=?", (status, result_digest, failure_kind, output_digest, envelope_digest))
            db.execute("UPDATE jobs SET status=?, result_ref=?, updated_at=? WHERE task_digest=? AND task_type='external'", (JobStatus.COMPLETED.value, result_digest, float(self._clock()), envelope_digest))
            db.commit()

    def resolve_task(self, task_ref: str) -> AgentTask:
        """Resolve an ephemeral task; reopened queues need an explicit resolver."""
        return self._tasks[_ref(task_ref, "task_ref")]

    def claim(self, worker_id: str, *, job_id: str | None = None) -> JobRecord | None:
        worker_id = _ref(worker_id, "worker_id")
        if job_id is not None:
            job_id = _ref(job_id, "job_id")
        now = float(self._clock())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            self._recover_expired(db, now)
            query = """SELECT * FROM jobs
                   WHERE status IN (?, ?) AND task_type <> 'external' AND available_at <= ? AND cancel_requested = 0"""
            arguments: list[object] = [JobStatus.QUEUED.value, JobStatus.RETRYABLE.value, now]
            if job_id is not None:
                query += " AND job_id = ?"
                arguments.append(job_id)
            query += " ORDER BY available_at, created_at, job_id LIMIT 1"
            row = db.execute(query, arguments).fetchone()
            if row is None:
                db.commit()
                return None
            attempts = int(row["attempts"]) + 1
            lease_until = now + self.lease_seconds
            lease_token = stable_digest({"job_id": row["job_id"], "worker_id": worker_id, "attempt": attempts, "lease_until": lease_until})[:32]
            db.execute(
                "UPDATE jobs SET status=?, attempts=?, worker_id=?, lease_until=?, lease_token=?, updated_at=? WHERE job_id=?",
                (JobStatus.RUNNING.value, attempts, worker_id, lease_until, lease_token, now, row["job_id"]),
            )
            self._event(db, row["job_id"], JobStatus.RUNNING.value, now, worker_id=worker_id)
            claimed = db.execute("SELECT * FROM jobs WHERE job_id = ?", (row["job_id"],)).fetchone()
            assert claimed is not None
            db.commit()
            return self._row(claimed)

    def retry(
        self,
        job_id: str,
        reason: str,
        *,
        worker_id: str | None = None,
        attempt: int | None = None,
        lease_until: float | None = None,
        lease_token: str | None = None,
    ) -> JobRecord:
        job_id = _ref(job_id, "job_id")
        reason_digest = stable_digest(str(reason))
        now = float(self._clock())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._must_row(db, job_id)
            status = JobStatus(row["status"])
            if status in {JobStatus.CANCELLED, JobStatus.COMPLETED, JobStatus.FAILED}:
                raise ValueError("terminal job cannot be retried")
            self._assert_fence(row, worker_id=worker_id, attempt=attempt, lease_until=lease_until, lease_token=lease_token, now=now)
            if row["cancel_requested"]:
                db.execute("UPDATE jobs SET status=?, worker_id=NULL, lease_until=NULL, lease_token=NULL, updated_at=? WHERE job_id=?", (JobStatus.CANCELLED.value, now, job_id))
                self._event(db, job_id, JobStatus.CANCELLED.value, now, reason_digest=reason_digest)
                result = self._must_row(db, job_id)
                db.commit()
                return self._row(result)
            attempts = int(row["attempts"])
            if attempts >= int(row["max_attempts"]):
                next_status = JobStatus.FAILED
                available_at = now
            else:
                next_status = JobStatus.RETRYABLE
                delay = min(self.backoff_max_seconds, self.backoff_base_seconds * (2 ** max(0, attempts - 1)))
                available_at = now + delay
            db.execute(
                """UPDATE jobs SET status=?, available_at=?, updated_at=?, worker_id=NULL,
                   lease_until=NULL, lease_token=NULL, last_error_digest=? WHERE job_id=?""",
                (next_status.value, available_at, now, reason_digest, job_id),
            )
            self._event(db, job_id, next_status.value, now, reason_digest=reason_digest)
            result = self._must_row(db, job_id)
            db.commit()
            return self._row(result)

    def cancel(self, job_id: str) -> JobRecord:
        job_id = _ref(job_id, "job_id")
        now = float(self._clock())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._must_row(db, job_id)
            status = JobStatus(row["status"])
            if status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                return self._row(row)
            if status is JobStatus.RUNNING:
                db.execute("UPDATE jobs SET cancel_requested=1, updated_at=? WHERE job_id=?", (now, job_id))
                result = self._must_row(db, job_id)
                db.commit()
                return self._row(result)
            db.execute(
                "UPDATE jobs SET status=?, updated_at=?, cancel_requested=1 WHERE job_id=?",
                (JobStatus.CANCELLED.value, now, job_id),
            )
            self._event(db, job_id, JobStatus.CANCELLED.value, now)
            result = self._must_row(db, job_id)
            db.commit()
            return self._row(result)

    def update_checkpoint(
        self,
        job_id: str,
        checkpoint_ref: str | None,
        *,
        worker_id: str | None = None,
        attempt: int | None = None,
        lease_until: float | None = None,
        lease_token: str | None = None,
    ) -> JobRecord:
        job_id = _ref(job_id, "job_id")
        if checkpoint_ref is not None:
            checkpoint_ref = _ref(checkpoint_ref, "checkpoint_ref")
        now = float(self._clock())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._must_row(db, job_id)
            self._assert_fence(row, worker_id=worker_id, attempt=attempt, lease_until=lease_until, lease_token=lease_token, now=now)
            db.execute("UPDATE jobs SET checkpoint_ref=?, updated_at=? WHERE job_id=?", (checkpoint_ref, now, job_id))
            self._event(
                db,
                job_id,
                "checkpoint_updated",
                now,
                worker_id=worker_id,
                attempt=int(attempt),
                lease_token_digest=stable_digest(lease_token or row["lease_token"])[:32],
            )
            result = self._must_row(db, job_id)
            db.commit()
            return self._row(result)

    def record_stage_checkpoint(
        self,
        job_id: str,
        stage_name: str,
        stage_ref: str,
        *,
        result_ref: str | None = None,
        status: str = "completed",
        worker_id: str | None = None,
        attempt: int | None = None,
        lease_until: float | None = None,
        lease_token: str | None = None,
    ) -> None:
        """Persist one stage's public references in the queue journal.

        Stage output payloads stay outside the queue.  A repeated stage write is
        idempotent only when it carries the same references, which prevents a
        late process from replacing a trusted checkpoint after a lease change.
        """
        job_id = _ref(job_id, "job_id")
        stage_name = _ref(stage_name, "stage_name")
        stage_ref = _ref(stage_ref, "stage_ref")
        result_ref = None if result_ref is None else _ref(result_ref, "result_ref")
        status = _ref(status, "status")
        now = float(self._clock())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._must_row(db, job_id)
            fenced = any(value is not None for value in (worker_id, attempt, lease_until, lease_token))
            if fenced:
                self._assert_fence(
                    row,
                    worker_id=worker_id,
                    attempt=attempt,
                    lease_until=lease_until,
                    lease_token=lease_token,
                    now=now,
                )
            existing = db.execute(
                "SELECT stage_ref, result_ref, status FROM stage_checkpoints WHERE job_id=? AND stage_name=?",
                (job_id, stage_name),
            ).fetchone()
            if existing is not None:
                if (existing["stage_ref"], existing["result_ref"], existing["status"]) != (stage_ref, result_ref, status):
                    db.rollback()
                    raise ValueError("stage checkpoint already exists with another digest")
                db.commit()
                return
            db.execute(
                "INSERT INTO stage_checkpoints(job_id, stage_name, stage_ref, result_ref, status, created_at) VALUES(?,?,?,?,?,?)",
                (job_id, stage_name, stage_ref, result_ref, status, now),
            )
            self._event(
                db,
                job_id,
                "stage_checkpoint",
                now,
                worker_id=worker_id,
                attempt=attempt,
                lease_token_digest=stable_digest(lease_token)[:32] if lease_token is not None else None,
            )
            db.commit()

    def stage_checkpoints(self, job_id: str) -> tuple[dict[str, object], ...]:
        """Return durable stage references without exposing local storage paths."""
        job_id = _ref(job_id, "job_id")
        with self._connect() as db:
            self._must_row(db, job_id)
            rows = db.execute(
                "SELECT stage_name, stage_ref, result_ref, status, created_at FROM stage_checkpoints WHERE job_id=? ORDER BY sequence",
                (job_id,),
            ).fetchall()
        return tuple(dict(zip(row.keys(), row)) for row in rows)

    def complete(
        self,
        job_id: str,
        *,
        result_ref: str,
        checkpoint_ref: str | None = None,
        report_ref: str | None = None,
        learning_ref: str | None = None,
        ledger_ref: str | None = None,
        worker_id: str | None = None,
        attempt: int | None = None,
        lease_until: float | None = None,
        lease_token: str | None = None,
    ) -> JobRecord:
        job_id = _ref(job_id, "job_id")
        result_ref = _ref(result_ref, "result_ref")
        refs = [checkpoint_ref, report_ref, learning_ref, ledger_ref]
        clean_refs = [None if value is None else _ref(value, "artifact_ref") for value in refs]
        now = float(self._clock())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._must_row(db, job_id)
            status = JobStatus(row["status"])
            if status is JobStatus.COMPLETED:
                db.commit()
                return self._row(row)
            if status is not JobStatus.RUNNING:
                raise ValueError("only running jobs can complete")
            self._assert_fence(row, worker_id=worker_id, attempt=attempt, lease_until=lease_until, lease_token=lease_token, now=now)
            if row["cancel_requested"]:
                db.execute("UPDATE jobs SET status=?, worker_id=NULL, lease_until=NULL, lease_token=NULL, updated_at=? WHERE job_id=?", (JobStatus.CANCELLED.value, now, job_id))
                self._event(db, job_id, JobStatus.CANCELLED.value, now)
            else:
                db.execute(
                    """UPDATE jobs SET status=?, updated_at=?, worker_id=NULL, lease_until=NULL,
                       lease_token=NULL, result_ref=?, checkpoint_ref=?, report_ref=?, learning_ref=?, ledger_ref=? WHERE job_id=?""",
                    (JobStatus.COMPLETED.value, now, result_ref, clean_refs[0], clean_refs[1], clean_refs[2], clean_refs[3], job_id),
                )
                self._event(db, job_id, JobStatus.COMPLETED.value, now)
            result = self._must_row(db, job_id)
            db.commit()
            return self._row(result)

    def fail(
        self,
        job_id: str,
        reason: str,
        *,
        worker_id: str | None = None,
        attempt: int | None = None,
        lease_until: float | None = None,
        lease_token: str | None = None,
    ) -> JobRecord:
        """Mark a job permanently failed without persisting the reason text."""
        job_id = _ref(job_id, "job_id")
        now = float(self._clock())
        reason_digest = stable_digest(str(reason))
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._must_row(db, job_id)
            status = JobStatus(row["status"])
            if status is JobStatus.FAILED:
                db.commit()
                return self._row(row)
            if status in {JobStatus.COMPLETED, JobStatus.CANCELLED}:
                raise ValueError("terminal job cannot be failed")
            self._assert_fence(row, worker_id=worker_id, attempt=attempt, lease_until=lease_until, lease_token=lease_token, now=now)
            db.execute(
                "UPDATE jobs SET status=?, worker_id=NULL, lease_until=NULL, lease_token=NULL, updated_at=?, last_error_digest=? WHERE job_id=?",
                (JobStatus.FAILED.value, now, reason_digest, job_id),
            )
            self._event(db, job_id, JobStatus.FAILED.value, now, reason_digest=reason_digest)
            result = self._must_row(db, job_id)
            db.commit()
            return self._row(result)

    def mark_cancelled(
        self,
        job_id: str,
        *,
        worker_id: str | None = None,
        attempt: int | None = None,
        lease_until: float | None = None,
        lease_token: str | None = None,
    ) -> JobRecord:
        job_id = _ref(job_id, "job_id")
        now = float(self._clock())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = self._must_row(db, job_id)
            if row["status"] == JobStatus.CANCELLED.value:
                db.commit()
                return self._row(row)
            if row["status"] in _TERMINAL:
                raise ValueError("terminal job cannot be cancelled")
            self._assert_fence(row, worker_id=worker_id, attempt=attempt, lease_until=lease_until, lease_token=lease_token, now=now)
            db.execute("UPDATE jobs SET status=?, worker_id=NULL, lease_until=NULL, lease_token=NULL, updated_at=? WHERE job_id=?", (JobStatus.CANCELLED.value, now, job_id))
            self._event(db, job_id, JobStatus.CANCELLED.value, now)
            result = self._must_row(db, job_id)
            db.commit()
            return self._row(result)

    def get(self, job_id: str) -> JobRecord:
        job_id = _ref(job_id, "job_id")
        with self._connect() as db:
            return self._row(self._must_row(db, job_id))

    def job_for_task(self, task_ref: str) -> JobRecord:
        """Resolve the current durable job by its public task reference."""
        task_ref = _ref(task_ref, "task_ref")
        with self._connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE task_ref=? ORDER BY created_at DESC LIMIT 1", (task_ref,)).fetchone()
            if row is None:
                raise KeyError(f"unknown task: {task_ref}")
            return self._row(row)

    def task_timeout(self, task_ref: str) -> float:
        task_ref = _ref(task_ref, "task_ref")
        with self._connect() as db:
            row = db.execute("SELECT task_timeout FROM jobs WHERE task_ref=? ORDER BY created_at DESC LIMIT 1", (task_ref,)).fetchone()
            if row is None:
                raise KeyError(f"unknown task: {task_ref}")
            return float(row["task_timeout"])

    def is_cancel_requested(self, job_id: str) -> bool:
        return bool(self.get(job_id).cancel_requested)

    def _recover_expired(self, db: sqlite3.Connection, now: float) -> None:
        rows = db.execute("SELECT * FROM jobs WHERE status=? AND lease_until IS NOT NULL AND lease_until <= ?", (JobStatus.RUNNING.value, now)).fetchall()
        for row in rows:
            if row["cancel_requested"]:
                status = JobStatus.CANCELLED
            elif int(row["attempts"]) >= int(row["max_attempts"]):
                status = JobStatus.FAILED
            else:
                status = JobStatus.RETRYABLE
            db.execute("UPDATE jobs SET status=?, worker_id=NULL, lease_until=NULL, lease_token=NULL, available_at=?, updated_at=? WHERE job_id=?", (status.value, now, now, row["job_id"]))
            self._event(db, row["job_id"], status.value, now)

    @staticmethod
    def _event(
        db: sqlite3.Connection,
        job_id: str,
        status: str,
        timestamp: float,
        *,
        reason_digest: str | None = None,
        worker_id: str | None = None,
        attempt: int | None = None,
        lease_token_digest: str | None = None,
    ) -> None:
        db.execute(
            "INSERT INTO job_events(job_id,status,timestamp,reason_digest,worker_id,attempt,lease_token_digest) VALUES(?,?,?,?,?,?,?)",
            (job_id, status, timestamp, reason_digest, worker_id, attempt, lease_token_digest),
        )

    @staticmethod
    def _must_row(db: sqlite3.Connection, job_id: str) -> sqlite3.Row:
        row = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown job: {job_id}")
        return row

    @staticmethod
    def _assert_fence(
        row: sqlite3.Row,
        *,
        worker_id: str | None,
        attempt: int | None,
        lease_until: float | None,
        lease_token: str | None,
        now: float,
    ) -> None:
        if row["status"] != JobStatus.RUNNING.value:
            raise StaleLeaseError("job is not running")
        if worker_id is None or attempt is None or (lease_token is None and lease_until is None):
            raise StaleLeaseError("worker lease fence is required")
        if row["worker_id"] != _ref(worker_id, "worker_id") or int(row["attempts"]) != int(attempt):
            raise StaleLeaseError("worker lease owner or attempt does not match")
        if lease_token is not None and row["lease_token"] != _ref(lease_token, "lease_token"):
            raise StaleLeaseError("worker lease token does not match")
        if lease_until is not None and (row["lease_until"] is None or float(row["lease_until"]) != float(lease_until)):
            raise StaleLeaseError("worker lease timestamp does not match")
        if row["lease_until"] is None or float(row["lease_until"]) <= now:
            raise StaleLeaseError("worker lease has expired")

    @staticmethod
    def _row(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"], task_ref=row["task_ref"], task_digest=row["task_digest"], idempotency_key=row["idempotency_key"],
            status=JobStatus(row["status"]), attempts=int(row["attempts"]), max_attempts=int(row["max_attempts"]),
            available_at=float(row["available_at"]), created_at=float(row["created_at"]), updated_at=float(row["updated_at"]),
            worker_id=row["worker_id"], lease_until=row["lease_until"], lease_token=row["lease_token"], last_error_digest=row["last_error_digest"],
            checkpoint_ref=row["checkpoint_ref"], result_ref=row["result_ref"], report_ref=row["report_ref"],
            learning_ref=row["learning_ref"], ledger_ref=row["ledger_ref"], cancel_requested=bool(row["cancel_requested"]),
            task_type=dict(zip(row.keys(), row)).get("task_type", "research"),
        )


__all__ = ["JobQueue", "JobRecord", "JobStatus", "StaleLeaseError"]
