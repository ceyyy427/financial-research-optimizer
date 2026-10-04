# P7.5 performance review

The local runtime is intentionally small: stdlib HTTP, SQLite, and the existing
P6/P7 modules. There is no vector database, browser bundle, or provider call in
the default path.

The HTTP E2E smoke test starts on loopback and completes the event, knowledge,
quant, strategy, personal save/reopen, community, and diagnostics requests in
one process. Knowledge search is an in-memory deterministic catalog lookup;
P7 writes are parameterized SQLite operations. Request bodies are capped at
1 MiB and responses use `Cache-Control: no-store` because the local app is a
research surface rather than a public cache.

Measure again before public hosting with a representative file-backed database,
large research exports, and a real browser. No performance claim is made for a
future multi-user service.
