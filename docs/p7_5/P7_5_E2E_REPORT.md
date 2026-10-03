# P7.5 E2E report

The executable coverage is in `tests/p7_5/test_local_app.py` and
`tests/p7_5/test_e2e.py`.

```text
./.venv/bin/pytest -q tests/p7_5/test_local_app.py tests/p7_5/test_e2e.py
6 passed
./.venv/bin/ruff check src/finahinking/local_app.py tests/p7_5/test_local_app.py tests/p7_5/test_e2e.py
All checks passed
```

The complete P7.5 test directory currently reports `11 passed`; the focused
HTTP/local-runtime subset above is six tests.

The HTTP smoke journey covers health, captured event, structured knowledge
search, quant experiment summary, strategy paper-only summary, private save,
personal export, reopen, community boundary, and diagnostics. A file-backed
test closes and recreates the application to prove persistence. The test uses a
proxy-free loopback opener, so external network state cannot influence the
result.
