# P7.5 information architecture

The product has calm, explicit worlds. Each world keeps the same evidence and
identity rather than creating a competing state machine.

| World | Purpose | Local surface |
| --- | --- | --- |
| HOME | Resume the next bounded action | `/` |
| EVENTS | Inspect a captured release and mechanism chain | `/events`, `/api/events`, `/api/events/learn` |
| EXPLORE / KNOWLEDGE | Search concepts, prerequisites, derivations, and paths | `/knowledge`, `/api/knowledge`, `/api/concepts/{id}` |
| QUANT | Question → hypothesis → experiment → result → evidence | `/quant`, `/api/quant` |
| STRATEGY LAB | StrategySpec through backtest, OOS, paper, and learning | `/strategy`, `/api/strategy` |
| PERSONAL | Private graph, history, mastery, and reopen | `/personal`, `/api/personal` |
| COMMUNITY | Evidence discussion and explicit projections | `/community`, `/api/community` |
| DIAGNOSTICS | Backend, database, source, and capability checks | `/diagnostics`, `/api/diagnostics` |

The first-run path is install → open HOME → inspect the sample CPI event → open
the linked concept path → run the sample quant explanation → save a private
note → close and reopen. Every source payload is labelled `LIVE`, `CAPTURED`,
`SAMPLE`, or `CACHED`; the default is `SAMPLE`/`CAPTURED`, never silently live.

The JSON surface is deliberately small and deterministic. Search is textual and
catalog-backed; a vector index is not installed because no measured capability
gap requires one.
