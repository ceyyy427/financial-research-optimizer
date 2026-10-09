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

- `PYTHONPATH=src /Users/mac/Documents/ChatGPT/Finahinking\ Autonomous\ Builder/.venv/bin/python -m pytest tests/p7_5/test_e2e.py -q`: **3 passed in 3.25s**.
- `npm test` in `frontend/`: **17 passed, 0 failed**. This includes runtime
  normalization, secret rejection, no-JS fallback, and render-only status checks.

The HTTP HTML responses are parsed directly by the tests. There is no saved
browser screenshot or browser execution evidence. Actual keyboard traversal,
screen-reader behavior, visual layout, responsive rendering and browser-engine
integration remain `EXTERNAL_UNVERIFIED`. No product/runtime implementation was
changed for this task.
