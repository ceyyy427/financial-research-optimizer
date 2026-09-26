# Agent execution and Plan DAG contract

The upper agent parses the user's task, creates an immutable research contract, and builds a bounded Plan DAG. It may choose a mode, source route, fallback, and next node, but it may not change the target, horizon, cutoff, costs, risk limits, or user constraints after seeing results.

Every node declares inputs, outputs, dependencies, success/failure conditions, retry count, timeout, budget, degradation permission, artifact paths, and provenance. `scripts/agent/planner.py` creates the DAG; `executor.py` only invokes registered Python handlers; `replanner.py` chooses at most one declared fallback per retry budget.

The permitted recovery order is:

```text
official API → official download → Patchright browser export → valid cache → degraded status → stop dependent analysis
```

Repeatedly reopening the same page is not a recovery strategy. A fallback must be visible in `node_result.json`, the provenance manifest, HTML, and decision table.

The browser is an access/observation adapter. Python owns canonicalization, point-in-time checks, modeling, validation, and artifacts. Agent actions are checked by `scripts/agent/policy_guard.py` and cannot place orders, bypass CAPTCHA/paywalls/access controls, expose credentials, or relax constraints.
