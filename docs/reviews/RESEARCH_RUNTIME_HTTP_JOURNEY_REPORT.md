# Research runtime HTTP journey verification

Date: 2026-10-09. Evidence class: `OFFLINE_PASS`.

Task 16 now has two concrete public HTTP tests in `tests/p7_5/test_e2e.py`,
using `_registered_runtime_app()` and `create_server()` on an ephemeral loopback
port. No external provider, live credential, browser, or Computer Use is involved.

The successful journey checks settings pages, a registered run, every linked
report, the schema v3 stream, no-JavaScript status content, semantic navigation,
password input behavior, injected-secret/path non-disclosure, and read-only POST
rejection. A second journey checks missing-run 404 failures for the run page,
report and stream without fixture fallback.

Validation actually executed:

- `PYTHONPATH=src /Users/mac/Documents/ChatGPT/Finahinking\ Autonomous\ Builder/.venv/bin/python -m pytest tests/p7_5/test_e2e.py -q`: **4 passed in 9.10s**.
- `npm test` in `frontend/`: **17 passed, 0 failed**. This includes runtime
  normalization, secret rejection, no-JS fallback, and render-only status checks.

The acceptance suite also uses Playwright 1.61 with the installed Chromium 1243
binary. It covers a registered failed run, JavaScript-disabled visible status,
password input and injected-secret non-disclosure, skip-link plus Tab traversal,
report navigation, desktop/mobile responsive overflow checks, and a visible
runtime error after a malformed stream response. Browser page and console errors
are collected and must be empty. Representative HTML and PNG evidence plus
SHA-256 hashes are saved under the ignored plan workspace at
`.superpowers/sdd/2026-10-08-research-capability-completion-plan/task-16-artifacts/`.

The run route now loads the bundled research script, making runtime stage
rendering and stream error handling browser-verifiable. The browser result is
`OFFLINE_BROWSER_PASS`; external provider connectivity, screen-reader
conformance, and production deployment remain `EXTERNAL_UNVERIFIED`.
