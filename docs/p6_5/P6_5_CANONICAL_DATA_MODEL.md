# P6.5 Canonical Data Model

## Boundary rule

Provider payloads stop at the adapter boundary. Finathink-owned immutable
records in `finahinking.p6_5.models` are the only objects that cross into
events, claims, persistence, explanations, and learning. Every record is
JSON-safe, validates bounded identifiers/text, and exposes a deterministic
SHA-256 fingerprint where an identity needs to be replayed.

## Entity catalogue

| Entity | Identity/grain | Important fields | Evidence/lineage rule |
| --- | --- | --- | --- |
| `Source` | one admitted publisher/source family (`source_id`) | publisher, owner, canonical URL, tier, decision, access method, usage/authentication conditions, source fingerprint | A source fingerprint is computed from the admission metadata; an aggregator is not authoritative merely because it is convenient |
| `SourceEndpoint` | endpoint within a source (`endpoint_id`) | URL, method, content type, rate limit, historical/revision behavior, availability semantics | Endpoint identity is separate from source identity; URL is allowlisted by the adapter |
| `SourceRelease` | source/endpoint/event/reference-period/release URL | `published_at`, optional source-bound `available_at`, release URL, schedule fingerprint | Publication is supplied by the official release document/schedule, not inferred from local retrieval |
| `TransportCapture` | one request/response capture (`capture_id`) | request fingerprint, status, headers, parser version, `retrieved_at`, `first_observed_at`, raw artifact ID, payload hash | Created before canonicalization; raw bytes remain replayable |
| `Artifact` (SQL) | immutable payload (`artifact_id`) | storage path, hash, byte length, creation time | Bytes are atomically written outside relational columns; hash is checked |
| `Measurement` | one finite metric/value/unit tuple | metric, value, unit | A small value object; BLS observations use the index unit |
| `Observation` | source/series/reference-period/dimensions | tuple of append-only `ObservationVersion`s | Logical grain is unique; versions are never overwritten |
| `ObservationVersion` | one value vintage (`version_id`) | value/unit, occurrence/effective/publication/availability/retrieval times, capture, revision status, supersession, footnotes | A missing/non-numeric source value is quarantined, not represented as a fake zero |
| `Event` | source/event type/reference period (`event_id`) | occurrence/effective/publication/availability times, observation IDs, evidence IDs, revision status | Event means something published/occurred; it is not an article or narrative summary |
| `Evidence` | one source/document/quant reference (`evidence_id`) | source, optional capture, reference, status, scope, limitations, source fingerprint | Evidence states what it supports and what it cannot establish |
| `Claim` | product statement (`claim_id`) | typed text, evidence IDs/status, source fingerprint, verification flag, limitations | A verified claim must resolve to matching trusted evidence; no arbitrary confidence number |
| `ClaimEvidenceLink` | claim/evidence pair | support type, scope, limitations | Many-to-many support is explicit and queryable |
| `Concept` | reusable concept (`concept_id`) | name, definition, optional formula, evidence IDs | Concepts explain terms; they do not turn theory into facts |
| `ConceptRelation` | directed concept edge (`relation_id`) | from/to IDs, relation type, evidence status, evidence IDs | Edge type distinguishes mechanism, supported relationship, historical association, and hypothesis |
| `Hypothesis` | event-scoped test (`hypothesis_id`) | statement/null, event, factor, benchmark, evaluation boundary, limitations | Sent to P6 only through the typed request path |

## CPI mapping

The first slice admits two BLS CPI series: `CUUR0000SA0` (CPI-U, not seasonally
adjusted) and `CUSR0000SA0` (CPI-U, seasonally adjusted). The adapter maps each
series and `YYYY-MM` period to one `Observation` with dimensions for area, item,
and adjustment. The December 2024 release creates a `MACRO_RELEASE` `Event`
linked to the selected observations and two direct-source evidence records (the
captured API response and the official release page). No consensus surprise or
market return is smuggled into the event because those would require separately
admitted sources.

## Fingerprints and serialization

Fingerprints hash canonical JSON with sorted keys, compact separators, UTF-8,
and NaN rejection. IDs are bounded identifiers rather than arbitrary paths.
Timestamp strings are retained with timezone information; normalization does
not erase the original capture/release references. `to_dict()` methods are
intended for audit/replay, not for accepting unvalidated external objects.

## Persistence mapping

The SQL migration mirrors the entity catalogue with normalized tables and join
tables. JSON-like dimensions, headers, footnotes, limitations, and evidence ID
lists are stored as bounded text in the portable migration. The SQLite adapter
stores raw payloads under a caller-owned artifact root and writes metadata with
fixed parameterized statements. PostgreSQL is the target system of record; the
SQLite adapter is deterministic test/dev infrastructure.

## Deliberate omissions

There is no provider-specific `Dataset` object crossing this boundary, no
generic undifferentiated `timestamp`, and no mutable “latest truth” column.
Specialized `MarketObservation`, Fed, SEC, A-share, consensus, and analogue
records are extension points, not part of the first slice. Revision-vintage
identity remains explicitly bounded when BLS does not expose one.
