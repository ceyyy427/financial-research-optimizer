# Tushare Pro Admission Review

**Provider:** [Tushare Pro](https://tushare.pro/)
**Source ID:** `tushare-pro`
**Tier:** `TIER_1` provider candidate
**Decision:** `DEFER`
**Review date:** 2026-10-03
**Production status:** Not admitted; no token, SDK, or connector installed

## Decision summary

Tushare Pro could be useful for future A-share research, including security
master data, listing/delisting dates, trading calendars, historical prices, and
fundamentals. It is a provider rather than the original publisher of every
field. P6.5 therefore classifies it as a TIER_1 candidate and **defers**
admission until account/credential controls, endpoint permissions and points,
terms, provenance, point-in-time behavior, revision semantics, and replay
evidence are reviewed for a defined dataset.

This is a provider-admission review, not a discovery-only shortcut: discovery
may identify a candidate endpoint, but it cannot authorize a Tushare response
for the canonical fact path.

This deferral is deliberate. It is not evidence that the provider is unusable,
and it is not permission to install the SDK or call the service.

## Official access evidence

The [official Pro data access documentation](https://tushare.pro/document/1?doc_id=40)
states that callers must register a Tushare community account and obtain a
token. It describes Python SDK and HTTP POST access, with request fields such
as `api_name`, `token`, `params`, and `fields`; responses contain a return code,
message, and `data.fields`/`data.items` payload. The docs also show permission
errors (for example code `2002`) and endpoint-specific data access.

The docs' example endpoint is `http://api.tushare.pro`. Any future production
adapter must perform a separate transport/security review and use an approved
TLS/endpoint policy; P6.5 does not treat an unencrypted example URL as an
authorization to send credentials.

## Publisher, owner, and terms

| Field | Finding |
| --- | --- |
| Provider/publisher of API service | Tushare Pro / Tushare community (verify current legal entity and service terms at admission time) |
| Underlying data owner | Endpoint-specific; may include exchanges, index publishers, regulators, or other providers. Tushare is not automatically the original publisher. |
| Authentication | Registered account plus secret token; endpoint permissions are tied to account points/entitlements. |
| Usage conditions | Current Tushare user/service agreements, endpoint terms, point limits, attribution, commercial use, and redistribution conditions must be reviewed. “Free token” does not imply unrestricted redistribution. |
| Credential policy | Never hardcode or commit a token. Use the project secret-management boundary and redact tokens from logs, captures, fixtures, and provenance. |
| Software | A Python SDK is documented, but installing it is outside P6.5 and requires a dependency/license/security review. |

The exact legal/usage terms and account rules can change. A future admission
must archive the reviewed terms URL/version and its review date.

## Access, rate, and endpoint stability

Tushare's API is a central provider endpoint with endpoint-specific points,
permissions, row limits, and rate limits. Official interface pages must be
consulted for each dataset. For example, the [stock_basic interface](https://tushare.pro/document/1?doc_id=25)
documents a row limit and points requirement; those numbers must not be
generalized to every endpoint.

Operational risks to resolve before admission include:

- token expiry, account suspension, and permission/points errors;
- endpoint-specific field additions/removals and SDK/API version changes;
- pagination and row-limit truncation;
- provider maintenance or rate limiting;
- whether HTTP examples are redirected or available over a validated TLS
  endpoint;
- whether a failed request is distinguishable from an empty dataset.

A future adapter must pin the API contract, bound timeouts/retries and pages,
capture status/body hashes and request parameters (with secrets redacted), and
fail closed on schema drift. It must not loop over all securities or dates
without an explicit bounded research contract.

## Historical support and revision behavior

Tushare documents historical fields for many interfaces, and its catalog
includes useful listing/delisting metadata. That establishes potential
coverage, not point-in-time correctness. Before admission, each dataset must
answer:

1. Is the row keyed by `ts_code`/`trade_date`, period/field, or another exact
   grain?
2. Can a historical query reproduce the value that was publicly available at a
   past decision time, or does it return today's revised value?
3. Are corporate-action adjustments, delistings, restatements, and corrections
   versioned or only overwritten?
4. Is there an official publication/release timestamp, provider availability
   timestamp, or vintage identifier?
5. Can a raw response and schema version be replayed independently of the
   provider?

Until those questions are answered, `published_at` and `available_at` remain
unknown for provider rows. `retrieved_at` is only the local capture time and
cannot be used as a release time. A revision must append a new observation
version with `supersedes_version_id` and preserve both raw captures.

## Grain and data-quality requirements

The candidate's likely grains include:

- security × trading date for daily prices;
- security × period × field for fundamentals;
- exchange × calendar date for trading calendars;
- security × listing-status interval for security master data.

These are examples, not an admitted schema. A future source record must state
the exact key, timezone/calendar, units, adjustment convention, missing-value
sentinels, pagination behavior, and duplicate rule. Required checks are schema
consistency, finite numeric values, date ordering, duplicate identity,
coverage, missingness, revision/vintage behavior, and reconciliation to the
underlying publisher where possible.

Provider output must remain distinguishable from official exchange/regulator
facts. A Tushare row can be evidence of “Tushare reported X at capture time”
only after a bounded research admission; it cannot be silently relabeled as an
SSE/SZSE/NBS fact.

## Failure and fallback policy

| Failure | Action |
| --- | --- |
| Missing/invalid token or permission code | Stop and report `DEFERRED/blocked`; never guess a token or bypass permission. |
| Points/row/rate limit | Stop within the declared budget; do not silently broaden accounts or loop requests. |
| HTTP/API error or empty response | Preserve status/message and request fingerprint; distinguish failure from a true empty result. |
| Schema or field drift | Quarantine capture; require contract review before parsing. |
| Missing vintage/availability evidence | Keep provider rows out of point-in-time claims and leakage-sensitive features. |
| Provider unavailable | Use an explicitly admitted official source or replay a named capture; never silently substitute AKShare/a-stock-data. |
| Source conflict | Preserve both provider and original-source observations and create a visible conflict. |

## Admission checklist for a future upgrade

Tushare can move from `DEFER` only after a review records:

- the exact dataset/endpoints and underlying publishers;
- current account, token, points, rate, and permission requirements;
- validated TLS/transport and secret redaction;
- terms, attribution, commercial and redistribution conditions;
- raw capture/replay, parser version, and schema/field contract;
- exact grain, historical coverage, duplicate/missingness/numeric checks;
- publication/availability/vintage and revision semantics;
- failure, rate-limit, and approved fallback behavior;
- a decision on `ADMIT_PROVIDER` versus `ADMIT_RESEARCH_ONLY`.

The first admission should be a narrow, low-risk dataset (for example a
trading calendar or security master) rather than a full A-share universe. A
production use must retain provider identity and must not claim that Tushare is
the original publisher.

## Installation decision

No Tushare SDK, plugin, MCP server, account token, or dependency was installed
or requested during P6.5. The candidate remains **TIER_1 / `DEFER`** until the
evidence above is collected under a separate authorized admission task.
