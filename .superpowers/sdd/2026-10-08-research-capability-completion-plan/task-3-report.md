# Task 3 report: compatible model provider contracts

## TDD

Added `tests/research/test_provider_live_contract.py` first and confirmed the
initial collection failure because `ProviderContractResult` was absent. The
tests cover successful OpenAI-compatible responses, DeepSeek-compatible setup,
401/403, 429, 5xx, timeout retry, non-JSON, schema mismatch, and bounded retry
exhaustion.

## Implementation

- Added the safe `ProviderContractResult` boundary and `invoke_contract` probe.
- Added standard chat-completions payload fields and parsing while retaining
  the injected `JsonTransport` interface and existing digest contract.
- Added bounded retries for 429/5xx and normalized provider failures without
  raw response, prompt, endpoint, or credential values.
- Added explicit `FINAHINKING_LIVE_PROVIDER_TEST` opt-in construction; no
  transport is created implicitly and default tests remain offline.

## Verification

- `python3 -m pytest tests/research/test_provider_adapters.py tests/research/test_provider_live_contract.py -q`: **25 passed**.
- `python3 -m pytest -q`: **798 passed, 1 skipped** (one existing fork warning).
