# P6.5 SQL Schema and Repository Boundary

## Target and test adapter

`migrations/001_p6_5_understanding.sql` is the additive P6.5 migration. The
target database is PostgreSQL. The repository currently ships a deterministic
`SQLiteUnderstandingRepository` using Python’s built-in `sqlite3` so tests can
exercise foreign keys, uniqueness, fixed queries, and artifact handling without
installing a host database or Python driver. Docker PostgreSQL 16 is the
verification environment for the target dialect.

The portable migration keeps JSON-shaped values as text and uses integer
boolean checks. These choices are intentional compatibility details, not a
claim that SQLite is the production system. A future reviewed migration may
promote selected columns to PostgreSQL `JSONB`.

## Tables and relationships

| Table | Role | Key constraints/indexes |
| --- | --- | --- |
| `p6_5_sources` | admitted publisher/source metadata | source ID PK, tier/decision checks, unique source fingerprint |
| `p6_5_endpoints` | endpoint behavior and availability semantics | source FK, method/boolean checks, unique source+URL+method |
| `p6_5_releases` | official release timing | source/endpoint FKs, unique source+event+period+URL |
| `p6_5_artifacts` | immutable raw payload metadata | artifact ID PK, unique payload hash, non-negative byte length |
| `p6_5_captures` | request/response metadata | source/endpoint/artifact FKs, HTTP status check, unique source+request hash+payload hash |
| `p6_5_observations` | logical observation grain | source FK, unique source+series+period+dimensions |
| `p6_5_observation_versions` | append-only values/times | observation/capture/self supersession FKs, revision enum, unique observation+version |
| `p6_5_events` | event identity and timing | source FK, revision enum, unique fingerprint |
| `p6_5_event_observations` | event-to-observation join | composite PK and both FKs |
| `p6_5_event_evidence` | event-to-evidence join | composite PK and event/evidence foreign keys |
| `p6_5_evidence` | evidence scope/status/limitations | source and optional capture FKs, evidence-status check |
| `p6_5_claims` | typed user-facing statements | claim/evidence-status checks, verified boolean check |
| `p6_5_claim_evidence` | many-to-many support | claim/evidence FKs, support-status check, composite PK |
| `p6_5_concepts` | definitions and formulas | concept ID PK |
| `p6_5_concept_relations` | directed mechanism/association edges | concept FKs and relation/status checks |
| `p6_5_hypotheses` | event-scoped test specifications | event FK, unique fingerprint |
| `p6_5_explanations` | progressive disclosure snapshot | event FK, explicit narrative slots |
| `p6_5_learning_refs` | learning artifact linkage | event/evidence/concept FKs and card fingerprint |
| `p6_5_observation_conflicts` | disagreement audit | observation/version FKs and fixed `SOURCE_CONFLICT` status |

Indexes cover observation availability, event source/period, claim/evidence
lookup, and capture first-observed time. They serve point-in-time lookup and
Show Evidence without introducing a mutable “current truth” table.

## Repository operations

The current adapter exposes fixed, parameterized methods:

- `apply_migration(connection)`;
- `save_source`, `save_endpoint`, `save_release`;
- `save_capture` (atomic raw-file write plus artifact/capture rows);
- `save_observation` (logical row plus all versions);
- `save_event` (event plus observation/evidence joins);
- `save_evidence`, `save_claim`, `link_claim_evidence`;
- `show_evidence(claim_id)` for user-facing source/provenance expansion.

Orphan claims are rejected before insertion. Foreign keys are enabled on the
SQLite connection. Every lookup value is passed as a bound parameter; a string
such as `claim-1' OR 1=1; DROP TABLE ...` is treated as an ID and returns no
rows. There is no generated table/column name path and no LLM-generated SQL.

## Raw payload policy

Raw payload bytes are preserved outside relational text columns under an
explicit artifact root. Artifact IDs are bounded to a safe identifier grammar;
the adapter checks root containment, writes a temporary file, flushes/fsyncs,
and atomically renames it. SQL records retain path, size, hash, capture times,
headers, parser version, and relationships. A payload is not normalized before
the raw artifact exists.

## PostgreSQL verification notes

The migration is intended to be applied with `psql` in an ephemeral
`postgres:16-alpine` container. Verification must assert that all tables,
foreign keys, checks, unique constraints, and indexes are created and that a
duplicate logical observation/orphan claim is rejected. The current Python
repository does not open a PostgreSQL connection directly; that is an explicit
production-integration gap, not hidden by the SQLite adapter.

## Known schema limitations

1. Direct database writers can still set the serialized `source_verified` flag
   without the process-local model token; production writes must remain behind
   the evidence resolver until a database-level signed envelope is added.
2. There is no migration-version ledger yet; deployment tooling must record the
   applied file externally until a reviewed migration table is added.
3. JSON text columns have application-level size/shape validation; PostgreSQL
   `JSONB` constraints are deferred.
4. A production Postgres repository/driver is not part of this P6.5 slice.

Evidence IDs stored inside the JSON/text `evidence_ids` fields on concepts and
similar narrative records are application-validated rather than individually
foreign-keyed. The normalized claim/evidence and event/evidence join tables do
carry database foreign keys; a future migration can normalize narrative
evidence arrays if those records become independently writable by untrusted
clients.

These limitations are gate-visible and do not authorize silently weakening
provenance or temporal checks.
