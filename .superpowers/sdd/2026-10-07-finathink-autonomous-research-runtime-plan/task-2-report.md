# Task 2 report: provider adapters and Codex bridge

## Implemented

- Added `provider_adapters.py` with provider-neutral JSON HTTP adapters for OpenAI-compatible and DeepSeek-compatible services. The transport, timeout, bounded retry policy, credential store/reference, and response schema version are injected. No provider SDK is used.
- An adapter has no default endpoint and returns a typed `NOT_CONFIGURED` failure until the caller supplies an explicit endpoint and transport. Model envelopes cannot request tools or URLs. Credentials are resolved only for the request and are never returned.
- Successful responses accept only the bounded research content schema. HTTP, timeout, non-JSON, schema, capability, and transport failures are normalized to `ProviderAdapterError` kinds without secret, endpoint, prompt, path, or raw provider details.
- Added `codex_bridge.py` with digest-only `CodexTaskEnvelope` creation and result acceptance. Handoffs are paper-only, have no tools, and contain request/context/prompt digests plus allowlisted capabilities. Missing external callbacks produce `EXTERNAL_HANDOFF_REQUIRED`; callback validation covers schema, input digest, capabilities, paper-only, duplicate result, and artifact boundaries.
- Updated `drivers.py` to map typed adapter failures to existing research `FailureKind` values, and tightened `provider_status.py` capability validation so status payloads never stringify arbitrary capability objects or expose unsafe names.
- Exported the new bridge and adapters from `finahinking.research`.
- Hardened the result boundaries after independent review: finish reasons are allowlisted; invalid Codex callbacks remain retryable; callback schemas are closed and require explicit `paper_only=True`; artifact references are digest/`artifact:` only; capabilities are finite and strictly named; credential references are provider-bound and single-source; empty provider content and parser/status ambiguity fail closed.

## TDD evidence

The new adapter and bridge tests were written before their implementation. The initial focused run failed during collection because concurrent Task 1 work temporarily defined duplicate `FailureKind` enum members in `contracts.py`; after that unrelated correction, the focused tests exercised missing modules and then the implementation failures. The final focused tests pass.

## Verification

```text
python3 -m pytest -q tests/research/test_provider_adapters.py tests/research/test_codex_bridge.py tests/research/test_provider_status.py tests/research/test_drivers.py
55 passed

python3 -m pytest -q tests/research
254 passed

python3 -m ruff check [Task 2 source and test files]
All checks passed!

python3 -m compileall -q src/finahinking/research
```

No real endpoint, provider SDK, Codex callback, credential value, or external network was used. The adapters remain mock/explicit-configuration boundaries by design.
