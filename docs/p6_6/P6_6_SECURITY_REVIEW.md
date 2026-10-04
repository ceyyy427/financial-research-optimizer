# P6.6 Security Review

## Boundary

The strategy idea is untrusted text. It is classified into two reviewed
templates and then represented by immutable JSON-safe `StrategySpec` and
`StrategyIR` records. The compiler allow-list is finite; no user text reaches
`eval`, `exec`, imports, shell, SQL, network, or a broker.

Educational `strategy.py` is an explanation artifact. The AST scanner rejects
imports, dynamic execution, filesystem/network access, credential terms, and
broker terms. The exporter never imports or executes that file, bounds each
file, rejects path traversal, and recursively rejects secret-shaped keys and
values.

`PaperRun` contains a virtual clock, signals, virtual orders, fills, and a
portfolio ledger only. It has no account, broker, credential, endpoint, or
submission operation. Historical and paper data must be supplied through an
approved immutable dataset reference; no new provider adapter or plugin was
installed.

## Review result

PASS for the deterministic P6.6 slice. Residual risks are documented rather
than hidden: source admission remains a P6.5 responsibility, timestamp quality
cannot be proved by a PIT check alone, and the educational artifact is not a
deployment package.
