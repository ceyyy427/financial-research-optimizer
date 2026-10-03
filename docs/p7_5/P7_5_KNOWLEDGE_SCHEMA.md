# P7.5 Knowledge Schema

The schema is represented by frozen dataclasses and serialises to stable JSON.
It is intentionally relational in shape even though the reference seed is
checked into Python: ids are normalised, links are explicit, and validation
rejects dangling edges and cycles.

| Record | Required fields | Links |
| --- | --- | --- |
| `KnowledgeConcept` | id, domain, intuition, formal definition, prerequisites | equations, derivations, suitable proofs, code, financial/quant/strategy/event applications, misconceptions, sources |
| `Equation` | id, expression, variables, meaning | owned by one concept |
| `DerivationStep` | id, statement, what changed, why valid, rule/theorem | ordered by tuple position |
| `CodeExample` | id, language, code, input/output contract | owned by one concept |
| `ApplicationLink` | id, type, title, description, target ids, role | financial, quant, strategy, or event |
| `Misconception` | id, claim, correction, source ids | source ids must exist on concept |
| `SourceReference` | id, title, kind, locator, notes | cited by concepts/misconceptions |
| `LearningPath` | id, title, type, concept ids, description | all concept ids must exist |
| `DomainCoverage` | id, title, category, scope, concept ids, source ids, status | maps every requested P7.5 domain to a reference or schema-ready slice |

The supported typed content vocabulary also includes `CONCEPT`, `DEFINITION`,
`THEOREM`, `EQUATION`, `DERIVATION`, `PROOF`, `ASSUMPTION`, `PREREQUISITE`,
`EXAMPLE`, `CODE_EXAMPLE`, `FINANCIAL_INTERPRETATION`, `QUANT_APPLICATION`,
`STRATEGY_APPLICATION`, `MISCONCEPTION`, `EXERCISE`, `SOURCE_REFERENCE`, and
`LEARNING_PATH`.

`KnowledgeCatalog.domain_coverage` explicitly represents mathematics (linear
algebra, calculus, optimisation), probability, statistics, econometrics
(regression and time series), quantitative research, portfolio/risk, asset
pricing, markets (equities, bonds, macro, derivatives), accounting/fundamentals,
behavioral science, and computer science for finance. A `REFERENCE` status is
authored in the initial slice; `SCHEMA_READY` records the supported extension
surface without pretending that an entire textbook domain was authored.

## Persistence decision

No second personal-state store or new required migration is introduced. The
reference catalog is immutable/versioned code data; P7 remains the source of
truth for private mastery, learning threads, research history, and community
projections. A future catalog ingestion migration may materialise these same
records, but it must preserve ids/fingerprints and cannot duplicate P7 state.
