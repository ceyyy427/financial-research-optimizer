# Task 2 report: secret-free provider credential boundary

## Modified files

- `src/finahinking/research/credentials.py`
  - Added the `CredentialStore` protocol.
  - Added `EnvironmentCredentialStore`, which accepts only explicit uppercase environment variable references and never exposes values in `str`/`repr`.
  - Added test-only `InMemoryCredentialStore` with redacted representation and no contract serialization support.
  - Added immutable `ProviderRuntimeConfig` and `build_provider_runtime`; construction validates configuration and readiness only and never resolves a secret or performs network I/O.
- `tests/research/test_credentials.py`
  - Added 15 tests for configured/missing credentials, invalid references and fields, secret-free representations, `ProviderSelection` separation, test-store serialization, and the no-network construction boundary.

## Verification

The new test file was run before implementation and failed with `ModuleNotFoundError: No module named 'finahinking.research.credentials'` (15 failures), confirming RED.

After implementation:

```text
$ python3 -m pytest -q tests/research/test_credentials.py
...............                                                          [100%]
15 passed in 0.45s
```

```text
$ python3 -m pytest -q tests/research/test_credentials.py tests/research/test_provider_config.py tests/research/test_provider_status.py
.....................                                                    [100%]
21 passed in 0.45s
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
- The shared worktree also contains untracked Task 1 files. They were not staged for this task's commit.
