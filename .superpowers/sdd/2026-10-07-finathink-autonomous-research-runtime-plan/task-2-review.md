# Task 2 review — resolved

Scope: hardening follow-up to commit `f6fe7bf`, addressing the independent
review findings against the Task 2 brief/spec.

## Resolution

- `finish_reason` now uses a finite string allowlist; unsafe values and custom
  objects fail schema validation before construction of `ModelResponse`.
- Invalid Codex callbacks no longer consume an envelope. A corrected callback
  can be accepted, while a valid accepted callback remains idempotently
  rejected as a duplicate.
- Codex callbacks use a closed JSON schema, require explicit
  `paper_only=True`, reject unknown/non-JSON/raw values recursively, and limit
  evidence references to `artifact:` or 64-hex digest references.
- Capabilities use a strict identifier and finite research allowlist, rejecting
  hyphenated execute/tool/network names and URL-like values.
- Credential references must match the adapter provider and select exactly one
  environment or keychain source.
- Provider content requires a non-empty status. HTTP status is classified
  before a response parser failure, keeping error kinds stable.

## Verification

- `python3 -m pytest -q tests/research/test_provider_adapters.py tests/research/test_codex_bridge.py tests/research/test_provider_status.py tests/research/test_drivers.py` => **55 passed**.
- `python3 -m pytest -q tests/research` => **254 passed**.
- `python3 -m ruff check` on all Task 2 source/test files => **All checks passed**.
- `python3 -m compileall -q src/finahinking/research` => **passed**.
