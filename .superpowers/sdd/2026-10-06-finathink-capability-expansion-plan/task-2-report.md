# Task 2 report: secret-free provider credential boundary

## Modified files

- `src/finahinking/research/credentials.py`
  - Added the `CredentialStore` protocol.
  - Added `EnvironmentCredentialStore`, which accepts only explicit uppercase environment variable references and never exposes values in `str`/`repr`.
  - Added test-only `InMemoryCredentialStore` with redacted representation and no contract serialization support.
  - Added immutable `ProviderRuntimeConfig` and `build_provider_runtime`; construction validates configuration and readiness only and never resolves a secret or performs network I/O.
- `tests/research/test_credentials.py`
  - Added 23 tests for configured/missing credentials, invalid references and fields, secret-free representations, `ProviderSelection` separation, test-store serialization, environment lookup isolation, capability allowlisting, normalized backend failures, and the no-network construction boundary.

## Verification

The new test file was run before implementation and failed with `ModuleNotFoundError: No module named 'finahinking.research.credentials'` (15 failures), confirming RED.

After implementation:

```text
$ python3 -m pytest -q tests/research/test_credentials.py
.......................                                                  [100%]
23 passed in 0.57s
```

```text
$ python3 -m pytest -q tests/research/test_credentials.py tests/research/test_provider_config.py tests/research/test_provider_status.py
.............................                                            [100%]
29 passed in 0.65s
```

The first hardening regression run produced six failures: pickle serialized the in-memory store, the environment mapping was enumerated/copied, capability values were stringified, store exceptions leaked, and the error-normalization helper was absent. The capability allowlist regression then produced three failures for unknown names before the allowlist was added.

The full research suite and full repository suite pass:

```text
$ python3 -m pytest -q tests/research
119 passed in 1.50s

$ python3 -m pytest -q
486 passed, 1 skipped in 37.48s
```

```text
$ python3 -m ruff check src/finahinking/research/credentials.py tests/research/test_credentials.py
All checks passed!
```

Full suite:

```text
470 passed, 1 skipped in 41.21s
```

## Unverified / concerns

- No real provider SDK, network request, timeout transport, or response parser was added by design. Provider timeout and malformed-response handling remains the responsibility of the provider adapter boundary; this task only guarantees that runtime construction does not resolve credentials or make a request.
- `normalize_provider_error` now gives stable `provider timeout`, `provider malformed response`, or `provider request failed` messages without echoing exception details. It is a pure boundary helper; it does not implement transport behavior.
- The shared worktree also contains untracked Task 1 files. They were not staged for this task's commit.
