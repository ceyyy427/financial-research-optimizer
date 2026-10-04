# P7 Personal Knowledge Graph

The graph is a private relational projection of a person's durable work. Nodes
are typed (`concept`, `claim`, `evidence`, `research`, `quant_run`, `strategy`,
`question`, `hypothesis`, `misconception`, `review_item`, and related types).
Edges are typed (`LEARNED`, `USED`, `QUESTIONED`, `TESTED`, `CONFUSED_WITH`,
`CORRECTED_BY`, `DERIVED_FROM`, `NEEDS_REVIEW`, and `SUPPORTED_BY`).

Every node and edge has one owner. Evidence links are references to existing
P5/P6/P6.5/P6.6 artifacts; the P7 repository never invents a financial fact or
replaces the authoritative quant output. Payloads are bounded JSON, sorted for
determinism, and retained as private data.

The graph supports three product loops:

1. Capture a question, research run, strategy run, or learning card.
2. Link evidence and mastery outcomes; surface misconceptions and open threads.
3. Re-enter a bounded, purpose-labeled context for a later explanation or
   review without exporting the entire history to an agent.

`authorized_context` is intentionally bounded and owner-scoped. Community
projections copy only selected source fields; graph traversal itself is never
public. Deletion uses foreign-key cascades for private graph material and an
audit-only record for accountability.
