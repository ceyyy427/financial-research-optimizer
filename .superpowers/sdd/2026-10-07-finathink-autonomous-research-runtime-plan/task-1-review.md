# Task 1 independent review follow-up

The review findings were addressed in the hardening commit:

- Live/order status strings are rejected for mapping results and direct
  `AgentOutcome` construction; all outcomes are required to remain paper-only.
- `AgentTask.inputs` is recursively JSON-safe and rejects sensitive keys,
  secret-like values, URI/path material, callables, and arbitrary objects.
  Public outcome identities, evidence references, and digests receive the same
  secret-free checks.
- Opaque deterministic gateways are retained only for an allowlisted role when
  the matching task capability is declared. Unrecognized objects are dropped
  from the driver context.
- Optional tasks now produce `OPTIONAL_FAILED` for exceptions, timeouts,
  invalid driver results, and typed driver failures; required tasks retain
  their blocking statuses.

Verification after the fixes: 20 focused tests passed, ruff passed, and
compileall passed. The full research collection remains blocked only by the
uncommitted Task 2/3 modules in the shared worktree.
