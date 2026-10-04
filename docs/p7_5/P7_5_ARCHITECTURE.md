# P7.5 Architecture

```text
Browser / local UI
        |
loopback HTTP shell (startup, routes, diagnostics, safe errors)
        |
P6.5 event/evidence  ── P7.5 typed KnowledgeCatalog ── P6.6 strategy lab
        |                         |
        +──────────── P7 repository / SQLite ──────────+
                         |
              private graph, learning state,
              provenance, consented projections
```

The Knowledge Engine is a typed, deterministic content authority. It does not
store per-user mastery; mastery and learning threads remain in P7. The local
shell is deliberately thin and may be replaced by a future desktop wrapper
without moving research or learning logic into the UI process.

## Persistence

SQLite is the default single-user database and uses the same additive P7
migration and owner-scoped repository. PostgreSQL remains an advanced target
through the existing migration path. Knowledge content is versioned code/data
with a catalog fingerprint; user state is persisted only through P7 contracts.

## Trust boundaries

The default server binds to loopback and sample mode makes no network call.
Source adapters and optional AI providers are explicit capabilities. Raw
claims, API keys, private research, and unconsented personal nodes never enter
community responses. No route can submit a broker or real-money order.
