# Task 16 browser acceptance report

Date: 2026-10-09. Evidence class: `OFFLINE_BROWSER_PASS`.

The acceptance test uses Playwright 1.61 and launches Chromium through
Playwright's own browser resolution (`chromium.launch(headless=True)`), so the
evidence does not depend on a machine-specific browser cache path. If the
bundled browser is not installed or cannot launch, the test skips with an
explicit `python -m playwright install chromium` message.
It starts the real loopback `create_server()` and injects only local, in-memory
research data. No provider, network, credential, or Computer Use call is made.

The test covers a failed registered run (`browser-failed-run`), JavaScript-disabled
rendering, password-field masking and secret non-disclosure, skip-link and Tab
focus traversal, report/run status text, desktop and 390px mobile layout with
`scrollWidth <= innerWidth`, visible failed stream-fetch handling, and browser
page/console errors. The failed stream response is a deliberately malformed
server-owned JSON response, so the UI schema failure path is exercised without
causing a browser network-console error.

Saved evidence is under:

`/Users/mac/.codex/worktrees/research-agent-runtime/Finahinking Autonomous Builder/.superpowers/sdd/2026-10-08-research-capability-completion-plan/task-16-artifacts/`

It contains `no-js-failed-mobile.html/.png`, `settings-desktop.html/.png`,
`settings-mobile.png`, `failed-stream-error.html/.png`, and `SHA256SUMS.tsv`.
The manifest contains one row per evidence file and deliberately excludes
`SHA256SUMS.tsv` itself; otherwise writing the manifest would immediately make
its own recorded size and digest stale. The test verifies every listed row
after writing the manifest.

The served run route now includes the bundled research script, so runtime stage
status and stream-fetch errors are exercised in the actual browser. The stale
packaged bundle was rebuilt from `frontend/src/research.js`; the generated site
copy is not part of this change. The CSP `frame-ancestors` token was removed
from the HTML meta policy because it is only valid in an HTTP response header;
the server header and `X-Frame-Options: DENY` remain authoritative.

Verification:

```text
PYTHONPATH=src /Users/mac/Documents/ChatGPT/Finahinking\ Autonomous\ Builder/.venv/bin/python -m pytest tests/p7_5/test_e2e.py -q
4 passed in 9.10s

cd frontend && npm test
17 passed, 0 failed
```

The evidence is local/offline and proves the tested Chromium journey only. It
does not prove external provider connectivity, production deployment behavior,
or screen-reader conformance.

## Retry verification (2026-10-09)

The portable browser test source and evidence manifest were rechecked after
removing the machine-specific executable path. In this checkout Playwright is
installed but its bundled Chromium binary is absent, so the real-browser case
skipped explicitly while the three HTTP/parser cases passed:

```text
python3 -m pytest -q tests/p7_5/test_e2e.py
3 passed, 1 skipped
SKIPPED: Playwright bundled Chromium is unavailable; run `python -m playwright install chromium`
```

The existing evidence manifest was regenerated with one row per evidence file;
`SHA256SUMS.tsv` is excluded from its own rows and each listed size/digest was
checked. The frontend suite was not rerun in this retry because only the
browser test and its report/manifest were changed.
