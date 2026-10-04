# BLS CPI Source Admission

**Source ID:** `bls`
**Tier:** `TIER_0`
**Decision:** `ADMIT_AUTHORITATIVE` (narrowly, for the captured CPI API/release scope)
**Review date:** 2026-10-03
**Owner:** U.S. Department of Labor, Bureau of Labor Statistics (BLS)

## Decision summary

BLS is the first P6.5 authoritative source because it is the original U.S.
statistical publisher, has a documented public time-series API, exposes stable
CPI series identifiers, and publishes an official release page with a public
release time. The P6.5 adapter admits only the BLS CPI series and response
grammar it can validate. It preserves the API response before parsing and
requires an official release bound for point-in-time availability.

This is not a blanket approval of every BLS program, endpoint, file, or future
API version. The admission scope is the endpoint, CPI series, release metadata,
and parser contract below.

## Official identity and references

| Item | Bound value |
| --- | --- |
| Publisher | [U.S. Bureau of Labor Statistics](https://www.bls.gov/) |
| Owner | U.S. Department of Labor |
| CPI series guide | [CPI series ID codes](https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm) |
| API documentation | [BLS API home](https://www.bls.gov/developers/home.htm) and [Python/API v2 example](https://www.bls.gov/developers/api_python.htm) |
| Admitted endpoint | `POST https://api.bls.gov/publicAPI/v2/timeseries/data/` |
| Official release evidence | [December 2024 CPI release](https://www.bls.gov/news.release/archives/cpi_01152025.htm) |
| Release schedule reference | [BLS schedules for news releases](https://www.bls.gov/schedule/news_release/) |
| Source identity | BLS API response + BLS release page; never an aggregator |

The December 2024 release page states an embargo/publication time of 8:30 a.m.
Eastern Time on Wednesday, January 15, 2025. P6.5 records that publication
timestamp as `published_at` and keeps the release URL as evidence. The page is
not treated as a substitute for the API row; both are linked.

## Admitted data scope and grain

The first fixture and parser scope includes:

- `CUUR0000SA0`: CPI-U, U.S. city average, all items, not seasonally adjusted;
- `CUSR0000SA0`: CPI-U, U.S. city average, all items, seasonally adjusted;
- regular monthly periods `M01`–`M12` represented as `YYYY-MM`;
- index values with BLS footnotes preserved;
- event period `2024-12` and the surrounding fixture rows used for replay and
  parser-quality checks.

The logical observation grain is:

```text
(source_id, series_id, reference_period, dimension set, observation version)
```

The parser's duplicate key is `(series_id, reference_period)` within one
capture. A duplicate is quarantined rather than selected by order. A future
series or dimension requires a new admission review; an unknown series is
quarantined as `unadmitted_series`.

The BLS [series-ID guide](https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm)
is the authority for interpreting the series code. The adapter does not infer
units or seasonal adjustment from a third-party label.

## Access, authentication, and terms

The API accepts JSON and documents `GET` for a single request and `POST` for
multi-series/multi-year requests. The P6.5 client uses only the allowlisted
JSON `POST` endpoint with bounded payload size, timeout, retries, and request
fingerprint. It does not follow an unallowlisted redirect.

BLS documentation distinguishes API versions and quota/registration paths.
The fixture/replay path requires no credential. Live use must follow the
current BLS registration, rate, and usage instructions; P6.5 does not embed a
registration token, claim unlimited access, or bypass a quota. The adapter
records relevant response headers when present and never stores credentials in
source records or fixtures.

Use of BLS data and redistribution of derived artifacts remains subject to the
current BLS site terms and applicable law. This admission is not legal advice
and does not grant a new redistribution license. Preserve BLS attribution and
the original URL in every downstream artifact.

## Endpoint stability and response contract

The endpoint and JSON response grammar are documented by BLS. The observed
shape admitted by `BLSCPIAdapter` is:

```json
{
  "status": "REQUEST_SUCCEEDED",
  "Results": {
    "series": [
      {"seriesID": "CUUR0000SA0", "data": [
        {"year": "2024", "period": "M12", "value": "315.605", "footnotes": []}
      ]}
    ]
  }
}
```

Only the observed object form of `Results.series` is accepted. A list-shaped
`Results`, missing `series`, malformed rows, or a source-reported failure is a
hard quarantine/error; the adapter does not guess a compatibility shape. The
parser version is stored with the capture so a later schema change can be
replayed and audited.

The official API page describes limits such as series-per-request, years per
request, and daily/request-rate quotas. The client imposes its own stricter
bounds (maximum 50 series, maximum 20 years, payload/capture size, timeout,
and at most three retries) so a source response cannot create an unbounded
operation.

## Historical support and revisions

BLS API requests historical observations by series and year. Historical support
is therefore admitted for the requested CPI series, but the API response does
not itself expose a complete public vintage identifier or a release timestamp
for every row. A later response may revise a historical value or add a
footnote. P6.5 consequently treats revision semantics as **unknown at the
API-row level** unless an official release/version artifact proves otherwise.

The canonical policy is append-only:

```text
Observation (logical key)
  -> ObservationVersion(original)
  -> ObservationVersion(revised, supersedes_version_id=<prior>)
```

Both captures, payload hashes, `published_at`, `available_at`, and
`retrieved_at` remain queryable. A conflict is visible; it is never overwritten
as if it had not existed. Historical research must choose the version whose
`available_at` is no later than the research cutoff, or stop if that bound is
unknown.

## Temporal and `available_at` semantics

For a monthly CPI row:

- `occurred_at` and `effective_at` are the first instant of the reference month
  (`YYYY-MM-01T00:00:00Z` in the canonical model);
- `published_at` comes from the official BLS release page/schedule, not from the
  API retrieval clock;
- `first_observed_at` is the earliest local capture observation time known to
  this run;
- `available_at` is the later of the official release bound and
  `first_observed_at` when both are present;
- `retrieved_at` is when this client captured the response.

The BLS API does not prove that a value was available before the first observed
capture. Therefore P6.5 does **not** set `available_at = retrieved_at` as a
general rule, and leaves the field unknown when no release bound is attached.
This distinction prevents look-ahead leakage in a historical `ResearchRun`.

## Missing values, footnotes, and quality behavior

The adapter treats a row with `value: "-"`, a non-numeric value, invalid month,
or an invalid row shape as a quarantined row. Footnotes (including a missing
value marker such as `X`) are retained in the quarantine record. The row is
never silently dropped or converted to zero/NaN. Numeric values must be finite.

Quality checks cover:

- source HTTP status and BLS `status` field;
- exact response schema and parser version;
- allowed series identifiers and monthly period grammar;
- duplicate `(series_id, reference_period)` keys;
- finite numeric values and unit consistency;
- temporal order `occurred_at <= effective_at <= published_at <= available_at <= retrieved_at` where fields exist;
- release-period matching for the event;
- raw payload hash and request fingerprint;
- replay equivalence between the fixture and the parser output.

## Failure and fallback behavior

| Failure | Action |
| --- | --- |
| DNS/timeout/connection/HTTP transport error | Bounded transport retry; after the ceiling, return a transport failure and no claim. |
| Redirect to a host other than `api.bls.gov` | Reject and preserve the failure context. |
| HTTP 200 with `REQUEST_FAILED` | Quarantine as a source failure; do not parse an empty/partial response as success. |
| Schema drift or malformed JSON | Quarantine; require parser review before admission continues. |
| Missing/non-numeric value or footnote marker | Preserve the row in quarantine; dependent event/claim is incomplete. |
| Duplicate logical key | Quarantine the duplicate and retain the first row only for the bounded parse result; no silent overwrite. |
| Missing release/availability evidence | Keep `available_at` unknown and block point-in-time dependent claims. |
| BLS temporarily unavailable | Replay an explicitly captured artifact for deterministic audit only; do not label it “latest.” |

There is no silent semantic fallback from BLS to AKShare, a-stock-data, or
another aggregator. A future alternate source must complete its own admission
and be shown as a separate source/conflict.

## Product and production decision

Within the admitted scope, BLS can support direct `FACT` claims such as “the
captured BLS CPI-U all-items index for December 2024 was X,” provided the claim
links to the API capture and official release evidence. It cannot by itself
support a causal claim, a next-day return prediction, consensus surprise, or a
trading instruction. Those require separately labeled interpretation,
hypothesis, quantitative evidence, and limitations.

The adapter is suitable for the P6.5 production-shaped vertical slice because
it has a narrow allowlist, raw capture/replay, deterministic parser, explicit
temporal fields, and fail-closed quality behavior. It is not a promise of
continuous live availability or a certification of every BLS dataset.

## Installation decision

No BLS plugin, MCP server, SDK, or extra Python dependency was installed.
P6.5 uses the existing standard-library HTTP boundary and an offline fixture;
live smoke, if run, is separate from deterministic CI and never upgrades
admission automatically.

