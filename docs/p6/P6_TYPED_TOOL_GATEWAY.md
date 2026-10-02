# P6 Typed Tool Gateway

The P6 gateway is a Finahinking-owned, policy-preserving facade aligned with
the frozen P5.5 `QuantServiceGateway` contract. It accepts only typed,
JSON-safe request models, binds each execution to an accepted experiment plan,
and dispatches the approved service names:

`quant.run_backtest`, `quant.run_regression`, `quant.evaluate_performance`,
`quant.analyze_risk`, `quant.compare_benchmark`, and `quant.inspect_run`.

The fixture implementation executes the admitted backtest, regression, and
read-only inspection handlers. The performance, risk, and benchmark names
remain in the stable allowlist; an unregistered handler returns a structured
`NOT_IMPLEMENTED` response rather than silently selecting a library.

Each request includes a question or hypothesis reference, experiment
specification, assumptions decision, provenance context, and request ID. Each
response includes status, normalized result, ResearchRun/QuantRun references
when applicable, result and artifact fingerprints, provenance, warnings,
limitations, and a structured failure code. The P6 layer never exposes a
statsmodels object, pandas object, callable, source string, or raw exception.

Execution is permitted only after `ASSUMPTIONS_ACCEPTED` and a plan fingerprint
match. Unknown and deferred tools return `REJECTED`; missing isolated adapters
return `UNAVAILABLE` without installation. A failed service produces no
evidence bundle. Inspection is read-only and bounded.

The gateway rejects arbitrary Python, shell, imports, package installation,
filesystem paths, URL fetching, eval/exec, source edits, artifact deletion,
provenance rewrites, and dynamic tool names. These checks occur before dispatch
and are covered by adversarial tests. An MCP transport, if added later, must
translate exactly into this boundary.
