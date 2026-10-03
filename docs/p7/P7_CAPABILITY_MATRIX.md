# P7 Capability Matrix

Audit date: 2026-10-03. The matrix records only capabilities inspected for this
mission. `Installed` means available in the current repository/environment, not
that a remote integration is authenticated.

| Capability | Required function | Existing tool / skill | Available | Trusted | Needs installation | Installed | Access scope | Security risk | P7 usage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Planning | Stage decomposition and gates | `superpowers:writing-plans`, repository docs | YES | YES | NO | YES | local repo | scope drift | plan and review gates |
| TDD/debugging | Red/green regression workflow | `superpowers:test-driven-development`, `superpowers:systematic-debugging` | YES | YES | NO | YES | local repo | false confidence | every P7 task |
| Code review | Independent audit | `superpowers:requesting-code-review`, software-engineering | YES | YES | NO | YES | local repo | missed defects | final A–J passes |
| Data quality | Orphan/duplicate/privacy consistency checks | `data-analytics:analyze-data-quality` | YES | YES | NO | YES | local repo artifacts | stale projections | review and tests |
| Security/privacy | Auth, projection, injection controls | repository-native policy + tests; security skill guidance | YES | YES | NO | YES | local app boundary | cross-user leak | identity/community |
| Relational persistence | Identity, ownership, FK, history | existing `p6_5` SQLite adapter + PostgreSQL migrations | YES | YES | NO | YES | local SQLite/PostgreSQL gate | integrity drift | migration 003 |
| Notebook/reproducibility | Deterministic research evidence | Jupyter + existing gates | YES | YES | NO | YES | local fixtures | non-repeatability | P6.6/P7 evidence |
| MCP/database connector | External database inspection | available MCP listing; not needed for local schema | YES | YES | NO | NO | none | scope/data egress | deferred |
| GitHub/issue connector | PR/community hosting | optional app capability | YES | YES | NO | NO | none | external write | deferred |
| Semantic/vector retrieval | Long-term recall | no measured gap; relational context first | NO | N/A | NO | NO | none | opaque memory | deferred |
| Graph database | Knowledge graph storage | no measured gap; typed relation tables suffice | NO | N/A | NO | NO | none | duplicate authority | deferred |
| Moderation SaaS | Community moderation | no measured gap; typed local policy/tests suffice | NO | N/A | NO | NO | none | external processor | deferred |
| Broker connector | Trading execution | explicitly prohibited by mission | NO | NO | NO | NO | none | financial harm | never admitted |
| Agent framework | Orchestration | existing guided orchestration | YES | YES | NO | NO | local application | authority expansion | reuse current code |

## Decision

There is no concrete P7 capability gap requiring installation. We will use the
existing repository-native relational and test architecture. No plugin, MCP
connector, Neo4j, pgvector, broker integration, SaaS community backend or agent
framework is installed. Any future admission requires a measured gap, trust and
permission review, explicit dependency record and a new approved phase.
