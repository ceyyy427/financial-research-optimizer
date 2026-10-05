# Research agent release checklist

- [ ] `python3 -m pytest -q tests/research` passes.
- [ ] Quant/P5/P8 regression tests pass with the offline default.
- [ ] `python3 -m compileall -q src tests` and `python3 -m ruff check src tests` pass.
- [ ] Frontend tests and build pass when the locked frontend dependencies are installed.
- [ ] Secret scan finds no API key, token, password, endpoint, absolute path, or complete prompt in reports, logs, checkpoints, examples, or fixtures.
- [ ] Every HTML bundle passes `verify_report_bundle`; JSON/Artifact facts and HTML claims have matching evidence and limitations.
- [ ] T+1, OOS, PIT/as-of, deterministic cost/slippage, risk gates, and provider-not-configured paths are covered by tests.
- [ ] Provider adapters remain optional and user-owned; no new SDK, network feed, paid data, broker, or real-money permission is enabled by default.
- [ ] Any unverified external prerequisite is written as an explicit limitation rather than reported as completed.
