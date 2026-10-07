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
compileall passed. At that point Task 2/3 modules were still being completed
in the shared worktree, so only the focused suite was used for that round.

The residual review round additionally verifies exact boolean paper flags,
capability intersection in `allowed_tools`, optional handling for all invalid
driver result shapes, finite numeric inputs, path/URI rejection, and strict
secret-free public outcome fields. Final verification is 25 focused tests and
259 research tests passed, with ruff and compileall clean.
