# SDD ledger — plan: docs/superpowers/plans/2026-10-10-worker-supervisor-spawn-task.md

Base: 06d16f2. Worktree: research-agent-runtime; branch codex/research-capability-roadmap. Preserve all earlier untracked files. No push/merge. Nine tasks pending.

## Preflight shared interfaces

| Tasks | Shared interface | Finding |
|---|---|---|
| 1/2/3/4/5/6 | invocation, stage names, result messages | Protocol needs attempt identity and sequencing before IPC consumers ship. |
| 2/3/4 | registry bootstrap | Registrations in parent memory do not exist under spawn; trusted startup descriptors must reconstruct registry, never task-controlled imports. |
| 3/4/8 | worker lifecycle | Worker handle starts children only from supervisor context; test harness may exercise handle directly. |
| 4/5/6 | queue, requests, leases, metrics | Digest-only queue cannot reconstruct requests; add private bounded request snapshot store and launch/config records. |
| 5/6 | limits and budget | Budgets must persist per job across attempts; global concurrency configured once, not by each caller. |
| 6/7 | checkpoint, terminal status, metrics | Only supervisor publishes durable state, including stage completion; unknown states are not successes. |
| 7/8/9 | docs and tests | Existing report/checklist evidence is stale; refresh from actual final commands. |
| 1/2/7 | __init__ exports | Stage registry import must have no startup/process side effects. |

## Self consistency

| Task | Test/code agreement |
|---|---|
| 1 | Exact per-kind payload shapes and digest/attempt fields need refinement. |
| 2 | Callable registration is startup-only; reconstruct in child via trusted descriptors. |
| 3 | Invocation requires a private request loader; no task-supplied import. |
| 4 | start is process creation; run_once/dispatch are supervisor-local, not API-thread entrypoints. |
| 5 | Explicit lifecycle changes require migration of callers/tests; private durable snapshots added. |
| 6 | Local budget cannot rely on parent ContextVar or shared values; aggregate deltas durably. |
| 7 | Resource failure kind is distinct from job terminal state; public snapshot reports both. |
| 8 | Reject legacy closures explicitly instead of cloudpickle/fork fallback; migrate tests to top-level fixtures. |
| 9 | Three full suites and twenty real concurrency runs, browser evidence if available. |

Ruling: Add private bounded JSON request snapshots with digest binding alongside the queue in Task 4/5 — spawn and restart cannot inherit _requests — costs a local persistence format/migration to maintain.
Ruling: Separate trusted bootstrap configuration (local paths, approved top-level callable descriptors) from task IPC/public artifacts; bootstrap never comes from a model or job payload — child must open its own resources and reconstruct registry — costs rejecting old arbitrary callable injections and documenting migration.
Ruling: Preserve strict result IPC while adding version/attempt identity and sequence binding; use parent wall deadline plus durable cumulative quotas across retries — stale/replayed messages must not publish — costs slightly richer internal protocol.
Ruling: Default workflow must fail closed on blocked research states and persist a verifiable artifact rather than synthesize a success digest — existing wrapper's digest-only success is insufficient — costs stronger integration tests and explicit blocked outcomes.

Correction: Earlier completion entries overstated review closure. Local passing tests are not independent review; unavailable or interrupted reviewers did not approve changes. Only explicit tool capacity errors prove capacity unavailability. Both gates below are reopened before dependent implementation proceeds.
Task 1: complete at c1d637f; 51 focused tests and Ruff pass; independent review approved strict RESULT, metrics, recursion/overflow, and invocation binding.
Task 2: complete at 6439cde; 8 focused tests and Ruff pass; scoped independent re-review approved fail-closed artifact behavior and preserved callable/digest gates.
Task 3: partial implementation at 4ace08d plus 3fac889; 9 focused spawn tests passed. Scoped review approved only the import-order fix, not every Task 3 acceptance criterion. Worker-local budget, bounded receive allocation, terminal-message latching, and all-stage validation still require verification. Legacy fork removal remains Task 8 work.
Task 4: incomplete at 92099ad plus 42e3cc3. 31 focused tests passed and scoped review approved dispatch startup recovery, but a daemon thread does not satisfy the required independent Supervisor process. Reopen architecture, cancellation, ownership, and restart gates before integration continues.
Task 5: incomplete draft committed at e44b9ee; 37 related tests passed, but independent reviewers were interrupted without a verdict. Callback resolver methods exist but are not wired into the new worker path; the default workflow receives WorkerInvocation rather than ResearchRequest. Stage routing still falls back when the reopened queue lacks ephemeral tasks. Metrics concurrency assertions were weakened to nonnegative retry counts; these do not demonstrate experiment isolation and must be restored with real worker charges. Explicit dedicated-process lifecycle and durable request loading remain required, not optional deferrals.
Task 6: interrupted draft preserved in observability.py, supervisor.py and related tests; uncommitted and not accepted. No further dependent implementation until Task 3–5 gates close.
Task 7: pending.
Task 8: pending.
Task 9: pending.

## Review evidence corrections and next gates

- Protocol tests at 0382d1c passed 44 tests, but the RESULT schema still accepted a generic `value` without a result reference. Decoder recursion was tested at construction only; deeply nested raw JSON could escape `json.loads` as RecursionError. These are the current Task 1 fix-round targets, not approved behaviors.
- A prior Task 2 report described SHA-256 syntax checks as verified persisted artifacts. No file content was verified by that code; the claim is withdrawn. Task 2 must reject in-memory-only claims and require file-backed verification before success.
- Broad package imports are a deferred minor footprint issue: existing package imports are not evidence of processes or network calls starting during registry import.
- Ruling: Stage callable admission is a correctness check on application-owned bootstrap code, not a sandbox against an attacker able to replace Python code objects and module exports — arbitrary-code resistance belongs to task-input isolation — cost if wrong is reworking the execution trust boundary.
- Ruling: Keep interrupted Task 3 changes uncommitted while Task 1/2 gates are closed; test and review them only after prerequisite approval — prevents accidental acceptance of unfinished spawn behavior — cost is later integration work.
- Ruling: Retain the pre-existing ResearchWorker fork path only as a temporary migration seam while Task 3 introduces SpawnWorkerHandle; Task 8 must remove the legacy path before release — avoids mixing the protocol implementation with the larger runtime-service migration — cost is a known interim fork finding in Task 3 review.
- Correction: The interim-thread ruling is withdrawn as an acceptance decision. It cannot override the task plan's explicit independent-process architecture. Thread-based code is a draft only.

## Current handoff evidence

- This request's Task 1 and Task 2 independent reviews are approved. Task 2 intentionally blocks unverified in-memory report claims; file-backed report publication is not implemented by that fix.
- Later implementation advanced before prerequisite acceptance. Those gates are reopened above, and no release/push/merge occurred.
- Full-suite run during Task 5: 998 passed, 2 skipped, 1 failed at tests/validation/test_artifact_install.py::test_wheel_install_exposes_migrations_fixtures_and_local_routes. Cause and baseline attribution are unverified; do not call it unrelated or pre-existing.
