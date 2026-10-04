# P8.2B Knowledge Content Standard

Canonical lessons are structured JSON records, not long UI strings. Every
`KnowledgeUnit` has identity, level, why-now context, background/history,
prerequisites, symbols, AST-backed equations, derivation/proof status,
assumptions, limitations, code-to-math anchors, applications, misconceptions,
exercises, provenance, and reference IDs. A unit cannot load if a prerequisite,
symbol, equation, proof step, code anchor, or citation is missing.

The initial local curriculum intentionally focuses on Returns, Volatility, OLS
and Beta, Sharpe, Momentum, and OOS/Overfitting. It is a flagship slice, not a
claim that every finance domain is authored. New contributions must add
validated references and deterministic tests; generated prose is never
automatically canonical.
