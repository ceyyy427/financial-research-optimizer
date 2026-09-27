# Agent execution and Plan DAG contract

The upper agent parses the user's task, creates an immutable research contract, and builds a bounded Plan DAG. It may choose a mode, source route, fallback, and next node, but it may not change the target, horizon, cutoff, costs, risk limits, or user constraints after seeing results.

Every node declares inputs, outputs, dependencies, success/failure conditions, retry count, timeout, budget, degradation permission, artifact paths, and provenance. `scripts/agent/planner.py` creates the DAG; `executor.py` only invokes registered Python handlers; `replanner.py` chooses at most one declared fallback per retry budget.

The first node is `contract_resolution`. Entity, target, horizon, cutoff,
calendar and execution conventions must resolve before source routing. An
unresolved field returns `needs_user_input` and blocks dependent analysis.

The Plan also carries one thread-safe global budget managed by
`scripts/agent/budget.py`: network requests, downloaded bytes, artifacts,
browser contexts and wall-clock time are reserved atomically across parallel
nodes. Node budgets are lower-level limits and cannot override the global cap.

Checkpoints are safe-resume records, not progress logs. They include
`run_id`, `plan_hash`, `contract_hash`, `schema_version`, environment/config
fingerprints, node attempts, artifact hashes, the last completed node and
`checkpoint_version`. A mismatch or corrupt checkpoint rejects resume with a
`checkpoint_mismatch` error rather than replaying an unverified state. The run
store keeps the same checkpoint in its JSON or SQLite backend, so a process
restart can resume without trusting an in-memory progress log.

The permitted recovery order is:

```text
official API → official download → Patchright browser export → valid cache → degraded status → stop dependent analysis
```

Repeatedly reopening the same page is not a recovery strategy. A fallback must be visible in `node_result.json`, the provenance manifest, HTML, and decision table.

The browser is an access/observation adapter. Python owns canonicalization, point-in-time checks, modeling, validation, and artifacts. Agent actions are checked by `scripts/agent/policy_guard.py` and cannot place orders, bypass CAPTCHA/paywalls/access controls, expose credentials, or relax constraints.
