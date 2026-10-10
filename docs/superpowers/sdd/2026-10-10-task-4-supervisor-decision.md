# Task 4 supervisor decision

## Decision

`ResearchSupervisor` owns the only `SpawnWorkerHandle` construction path and
opens a fresh `JobQueue` from the durable SQLite path. Its control loop is
isolated from request state and can be started/stopped independently; worker
processes always use the existing `spawn` handle. Queue lease, heartbeat,
checkpoint, retry, and terminal publication operations remain atomic and
fenced by `(worker_id, attempt, lease_token)`.

## Rationale

The Task 4 public API exposes synchronous `dispatch`/`run_once` calls as well
as `start`/`stop`, while Task 5 owns integration with the long-lived runtime
service. Keeping the supervisor control loop in its own daemon thread at this
boundary preserves the API contract and makes all process creation occur from
the supervisor owner, without introducing a second command IPC protocol before
Task 5. The durable queue is the restart boundary: a new supervisor instance
recovers expired leases and never trusts inherited queue connections or worker
objects.

## Scope boundary

This decision does not authorize request threads to create workers or retain a
fork fallback. A later service integration may host the same supervisor loop
inside a dedicated process, provided it preserves the queue fences and spawn
ownership established here.
