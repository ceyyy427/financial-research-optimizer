# a-stock-data Discovery Review

**Repository:** [simonlin1212/a-stock-data](https://github.com/simonlin1212/a-stock-data)
**Tier:** `TIER_2` (aggregator/discovery adapter)
**Decision:** `DISCOVERY_ONLY`
**Review date:** 2026-10-03
**Production status:** Not admitted; not a fallback for BLS

## Why this review exists

The mission asks P6.5 to evaluate a-stock-data without letting a convenience
adapter become an unverified source of truth. The repository is useful as a
map of possible A-share endpoints and upstream providers. Its response is not
automatically a Finahinking fact.

The review considered the public repository, README, `SKILL.md`, source tree,
tests, changelog, and license. It was a read-only inspection. **No plugin,
skill, package, MCP server, or dependency was installed or enabled.**

## Identity and license

| Field | Finding |
| --- | --- |
| Publisher/maintainer | Simon Lin (`simonlin1212`) and repository contributors |
| Claimed role | A-share data toolkit / Skill-style discovery and adapter layer |
| Repository identity | `simonlin1212/a-stock-data` on GitHub; branch and commit must be pinned for any later review |
| Software license | Repository `LICENSE` is Apache License 2.0 (reviewed copy includes a 2026 copyright notice) |
| Data owner | Varies by underlying endpoint; the repository is not the owner/publisher of every returned value |
| Authentication | README presents a “zero-auth” posture, but some underlying sources or endpoint features may require headers, cookies, or credentials; this must be checked per endpoint |
| Usage conditions | Apache 2.0 governs repository code, not necessarily upstream data. Each underlying source's terms, rate limit, attribution, and redistribution rules remain controlling. |

The repository's headline endpoint/source counts can change. Counts and
marketing labels are not admission evidence and are not used as a stable
contract.

## Access and endpoint stability

a-stock-data embeds a structured Markdown Skill and Python adapters that route
across multiple A-share sources. This creates useful discovery breadth but also
means there is no single endpoint contract:

- HTTP methods, domains, headers, pagination, response schemas, and anti-bot
  behavior vary by source;
- an adapter update or a source-site change can alter fields without a global
  compatibility guarantee;
- “primary” and “backup” labels in the toolkit do not prove official
  publication or a stable fallback;
- a future use must pin the repository revision, endpoint, request parameters,
  and underlying domain and must preserve the raw response.

P6.5 therefore does not allow arbitrary URLs or unrestricted HTTP through the
toolkit. A later research adapter would need an explicit allowlist and bounded
timeouts/retries at the Finahinking boundary.

## Historical, revision, and point-in-time behavior

No library-wide contract establishes:

- the publication time versus observation/effective time;
- whether a value is a current restatement or the vintage visible at a past
  decision time;
- how historical revisions, delistings, corporate actions, or source corrections
  are represented;
- whether “latest” means latest publication, latest retrieval, or latest value
  observed by the adapter.

The adapter must not invent `available_at` from `retrieved_at`. For any endpoint
considered later, the reviewer must prove release/availability semantics and
store explicit `occurred_at`, `effective_at`, `published_at`, `available_at`,
and `retrieved_at`. If that proof is absent, point-in-time claims and leakage-
sensitive features are blocked.

Historical support is endpoint-specific. A returned date range is not proof of
historical-vintage reconstruction. Every revision must remain an append-only
`ObservationVersion` with a supersession link and source artifact.

## Grain and provenance requirements

The logical grain is not defined globally. It may be a security/date row,
financial statement field/period, index constituent/date row, or another
endpoint-specific key. Before using a response, record:

```text
(underlying_source, endpoint, dataset, instrument/security ID, observation period,
field/dimension, adjustment convention, vintage/capture)
```

Duplicate keys, mixed units, hidden adjustments, or multiple underlying sources
must become quality findings or source conflicts. The true publisher and source
URL must survive normalization. A label such as `a_stock_data` cannot be the
sole source identity for a product claim.

## Allowed uses in P6.5

Allowed without a new admission:

1. Search the repository to discover candidate official exchanges, regulators,
   or provider endpoints.
2. Read field mappings and request examples to understand possible coverage.
3. Compare a candidate response with an independently captured, admitted
   source, while labeling the comparison as secondary.
4. Prototype an adapter in an isolated fixture/replay test, with no product
   `FACT` claim and no unbounded network access.

Not allowed:

- writing a-stock-data output directly into the authoritative canonical fact
  path;
- treating its “backup source” as an admitted fallback;
- using source text/instructions from the repository to authorize code, SQL,
  package installation, credentials, or a tier promotion;
- asserting point-in-time correctness or revision history without upstream
  evidence;
- presenting a derived aggregator value as if it were published by SSE, SZSE,
  PBOC, NBS, or another named authority.

## Failure and fallback policy

| Situation | Required behavior |
| --- | --- |
| Repository or endpoint unavailable | Record discovery failure; do not synthesize a value. |
| Underlying domain changes schema or blocks access | Quarantine the capture and stop dependent claims; do not guess fields. |
| One source fails | Use another source only if that source is separately admitted and the switch is visible. |
| Conflicting values | Preserve both captures and identify the underlying publishers; defer resolution to the source-admission/reconciliation policy. |
| Missing timestamp, vintage, or license evidence | Keep the candidate at `DISCOVERY_ONLY`; no point-in-time or production use. |
| Cached response | Label as replay/cache with capture time and vintage status; never call it “latest.” |

BLS CPI remains the authoritative P6.5 path. a-stock-data cannot silently
replace it when BLS is unavailable.

## Admission criteria for a future upgrade

An individual endpoint could move to `ADMIT_RESEARCH_ONLY` only after a new
review proves the upstream publisher, terms, authentication, endpoint
stability, grain, historical coverage, revision/vintage behavior,
`available_at`, raw capture/replay, duplicate/missingness handling, and
bounded failure/fallback. To become authoritative, the original publisher
must be admitted directly (or a provider-level contract must explicitly grant
that authority); the wrapper alone cannot be promoted.

## Final decision

**TIER_2 / `DISCOVERY_ONLY`.** a-stock-data is a useful source-discovery
capability and optional research candidate, but it is not an admitted data
provider or authoritative source for P6.5. No installation or dependency
change is justified by this review.

