# P7 Independent Review C — Security

**Review date:** 2026-10-03  
**Track:** C — authorization, injection, untrusted content, and tool boundary  
**Decision:** **PASS — bounded local P7 slice; not production approval**

## Review scope

This pass checks trusted-session authorization, owner and room permissions,
parameterized SQL, inert community content, validated links, and the absence of
a P7 path that can invoke tools or mutate earlier factual/quantitative
authorities.

## Evidence inspected

- P7 repository values are SQL parameters; mutation paths roll back on
  integrity failures where partial writes could leak or persist.
- Models validate enums, JSON safety, non-finite values, payload size, post and
  comment status, and community claim labels. Room membership and attachment
  visibility are checked before writes.
- Session lifecycle and removed-membership cases are in
  `tests/p7/test_adversarial_boundaries.py`; SQL metacharacter and private
  access cases are in the focused tests.
- `rg -n "eval\\(|exec\\(|compile\\(|subprocess|os\\.system|shell=True"
  `src/finahinking/p7 tests/p7` returns no matches.

## Fresh command evidence

- Requested baseline: **8 P7 passed**, with each full environment at
  **223 passed, 1 skipped**; current adversarial set is **11 P7 passed** and
  **226 passed, 1 skipped** in each full environment.
- `make p5-5-gate` passes Ruff and all regression checks.
- `bash -n scripts/verify_p6_5_postgres.sh` and the disposable PostgreSQL
  migration gate pass.

## Local-slice acceptance

The bounded repository surface fails closed for session, owner, room, stale
projection, duplicate, and cross-owner cases. No executable/tool-dispatch path
exists in P7, and static dangerous-call inspection is clean. Security passes
for this local scope.

## Residual production risks (non-blocking for this bounded slice)

- Future agent/tool integration needs a separate content-as-data boundary,
  prompt-injection tests, link/HTML rendering policy, and explicit tool
  allowlists. P7 currently has no dispatcher to certify.
- A production PostgreSQL adapter needs concurrency, isolation, timeout,
  rollback, and authorization tests in addition to the schema gate.
- Artifact links should resolve trusted P4–P6.6 authorities and verify source
  provenance/code commits instead of accepting caller-supplied references.
- Rate limits, abuse monitoring, key management, and security incident
  response are outside this local Stage B slice.

Security passes for the bounded local P7 slice; residuals do not block local
continuation or imply production security sign-off.
