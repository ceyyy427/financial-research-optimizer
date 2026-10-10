# SDD ledger — plan: docs/superpowers/plans/2026-10-10-worker-supervisor-spawn-task.md

Base: 06d16f2. Worktree: research-agent-runtime; branch codex/research-capability-roadmap. Preserve all earlier untracked files. User authorized push/merge/publish after gates. Nine tasks in progress.

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
Task 3: complete at 4ace08d, 3fac889, 9c33f43, and 5ab0770; bounded receive allocation, terminal-message latching, all-stage result validation, trusted registry reconstruction, worker-local budget, and spawn-only compatibility are covered by focused tests.
Task 4: complete at 34c8f54; Supervisor is a non-daemon independent spawn process with private queue/registry reconstruction, bounded worker ownership, durable lease recovery, and idempotent publication. Process PID and restart-oriented tests pass.
Task 5: complete at 5ab0770 plus the final hardening pass; service persists request snapshots atomically with queue visibility, binds resolver/snapshot digests to the durable task input, rejects secret/path-like values, and default stages load the expected digest. No request thread creates workers.
Task 6: complete at 9c33f43 plus 34c8f54 and final hardening; worker-local limits are persisted per job and reach spawned workers, failure/cancel/resource metrics are durable, and Supervisor stop clears active leases. Focused runtime/supervisor/worker/spawn tests passed; supervisor metrics pair repeated 20 times without intermittent failure.
Task 7: complete in existing report/UI implementation plus 5ab0770 documentation refresh; report and runtime UI tests pass, public views remain redacted server snapshots. Browser evidence remains local/offline only.
Task 8: complete at 5ab0770; legacy ResearchWorker path uses spawn only, rejects nested/lambda callables, and migrated callers/tests to importable top-level fixtures. Focused worker/codex/vertical/runtime/supervisor/spawn tests passed (56).
Task 9: implementation gates complete locally: compileall, Ruff, governance, pip check, frontend 17/17, browser 4/4, full Python suite 1025 passed/1 skipped, and the process-owned concurrency test 20/20. Independent review findings were repaired: unknown capabilities fail closed, control IPC is bounded/exact, request identity is atomic and digest-bound, per-job budgets reach workers, stop cleans leases, terminal metrics persist, and observer wall expiry durably cancels/releases leases.

## Review evidence corrections and next gates

- Protocol tests at 0382d1c passed 44 tests, but the RESULT schema still accepted a generic `value` without a result reference. Decoder recursion was tested at construction only; deeply nested raw JSON could escape `json.loads` as RecursionError. These are the current Task 1 fix-round targets, not approved behaviors.
- A prior Task 2 report described SHA-256 syntax checks as verified persisted artifacts. No file content was verified by that code; the claim is withdrawn. Task 2 must reject in-memory-only claims and require file-backed verification before success.
- Broad package imports are a deferred minor footprint issue: existing package imports are not evidence of processes or network calls starting during registry import.
- Ruling: Stage callable admission is a correctness check on application-owned bootstrap code, not a sandbox against an attacker able to replace Python code objects and module exports — arbitrary-code resistance belongs to task-input isolation — cost if wrong is reworking the execution trust boundary.
- Ruling: Keep interrupted Task 3 changes uncommitted while Task 1/2 gates are closed; test and review them only after prerequisite approval — prevents accidental acceptance of unfinished spawn behavior — cost is later integration work.
- Correction: The interim-fork ruling is withdrawn. Both the normal Supervisor path and the compatibility ResearchWorker path now use spawn; no automatic fork fallback remains.

## Current handoff evidence

- This request's Task 1 and Task 2 independent reviews are approved. Task 2 intentionally blocks unverified in-memory report claims; file-backed report publication is not implemented by that fix.
- Later implementation advanced before prerequisite acceptance. Those gates are reopened above, and no release/push/merge occurred.
- Full-suite run during Task 5: 998 passed, 2 skipped, 1 failed at tests/validation/test_artifact_install.py::test_wheel_install_exposes_migrations_fixtures_and_local_routes. Cause and baseline attribution are unverified; do not call it unrelated or pre-existing.
- Packaging follow-up: clean wheel/install/probe passed repeatedly and `scripts/clean_install.py` passed; 9fc09ba now surfaces subprocess stderr. Deliberate offline build isolation failure is only missing pinned setuptools, not a package defect.
- Task 9 evidence: `/tmp/finathink-pytest-run1.log`, `/tmp/finathink-pytest-run2.log`, `/tmp/finathink-pytest-run3.log`; browser acceptance `tests/p7_5/test_e2e.py` 4 passed after installing Playwright Chromium.
