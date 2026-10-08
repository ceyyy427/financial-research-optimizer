# Task 2 report: user model provider configuration

Implemented `ProviderConfig` and `ProviderConfigStore` in `src/finahinking/research/provider_config.py`.

- Provider settings are validated through explicit adapter/model/role allow-lists.
- Endpoints must be credential-free HTTPS URLs; userinfo, query strings, fragments, private hosts, local hosts, and secret-like paths are rejected.
- Credential values are never accepted by the model configuration object or persisted. Only the existing `ProviderCredentialRef` (environment variable or keychain label) is retained. The keychain readiness helper reuses `KeychainDataCredentialStore` and does not resolve values into configuration.
- JSON persistence is atomic and restart-readable. Duplicate provider IDs are rejected; remove/get/list and role-to-model lookup are supported. `list()` and route responses expose only redacted fields, including `endpoint_configured` rather than the endpoint itself.
- Added CSRF-protected `GET/POST /api/research/providers/config`. POST accepts only the provider configuration allow-list; raw secret fields are rejected and no provider is called. Saved configurations participate in the existing secret-free provider readiness payload.

## Validation

- Red phase: `python3 -m pytest tests/research/test_provider_config.py -q` failed at collection because `provider_config` did not exist; route tests then failed with the expected missing-route 404.
- Focused green: `python3 -m pytest tests/research/test_provider_config.py tests/research/test_provider_status.py tests/research/test_credentials.py tests/research/test_provider_adapters.py tests/research/test_ui.py tests/p7_5/test_local_app.py -q` → **70 passed**.
- Full suite: `python3 -m pytest -q` → **780 passed, 1 skipped, 1 warning**. The warning is Python 3.13's multiprocessing fork deprecation from `tests/research/test_autonomous_runtime_vertical_slice.py::test_factor_risk_portfolio_and_worker_fail_closed`; it is unrelated to provider configuration.

## Concerns

- The store uses atomic JSON persistence; it does not introduce a new SQLite migration. In-memory local app instances intentionally use process-local configuration because there is no restartable path.
- Endpoint URLs are retained in the private on-disk configuration for later adapter construction but are omitted from all list and route responses.
