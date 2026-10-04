# AKShare Admission Review

**Repository:** [akfamily/akshare](https://github.com/akfamily/akshare)
**Tier:** `TIER_2` (aggregator/adapter)
**Decision:** `DISCOVERY_ONLY` (research candidate; no endpoint is admitted in P6.5)
**Review date:** 2026-10-03
**Production status:** Deferred pending endpoint- and upstream-specific admission

## Scope and conclusion

AKShare is a broad open-source Python interface library that collects data from
many public websites and providers. It is useful for discovering coverage,
learning field names, and performing bounded cross-source research. It is not a
single publisher and its interfaces do not share one trust, timestamp, license,
or revision contract.

P6.5 keeps AKShare at TIER_2 / `DISCOVERY_ONLY`. A particular interface may be
reviewed later for `ADMIT_RESEARCH_ONLY`, but only after its underlying source
is identified and the full admission contract is satisfied. No AKShare package,
plugin, MCP server, or dependency was installed for this review.

## Evidence reviewed

| Evidence | Relevance |
| --- | --- |
| [AKShare repository](https://github.com/akfamily/akshare) | Project identity, source tree, release activity, and interface inventory |
| [Project introduction](https://github.com/akfamily/akshare/blob/main/docs/introduction.md) | States that interfaces collect public data and are intended primarily for academic research; explains that source pages can change and interfaces need maintenance |
| [Project README](https://github.com/akfamily/akshare/blob/main/README.md) | Data-use notices, interface caveats, and project scope |
| [License](https://github.com/akfamily/akshare/blob/main/LICENSE) | MIT license for the software repository; not a blanket license for upstream data |
| [Tutorial/interface search](https://github.com/akfamily/akshare/blob/main/docs/tutorial.md) | Shows that interface names and fields are endpoint-specific |

The project documentation itself warns that interfaces may be removed or stop
working when target pages change and asks users to follow the relevant
open-source/data protocols. Those are operational signals, not a criticism of
the project; they are why admission must be narrow.

## Publisher, owner, and usage conditions

| Field | Finding |
| --- | --- |
| Software maintainer | AKFamily / project contributors |
| Software license | MIT (repository `LICENSE`) |
| Data publisher/owner | Varies by interface: exchanges, public agencies, financial websites, or other upstream providers |
| Access | Python functions; AKTools may expose an HTTP form of the library; each interface has its own URL/method/headers and response schema |
| Authentication | Often no user token in the library call, but upstream sites may require cookies, headers, anti-bot behavior, or other authorization; never infer “public” means unrestricted redistribution |
| Terms | AKShare README/introduction describe data as for academic research/reference and advise attention to data risk. Upstream site terms remain controlling. Verify commercial use, scraping, caching, and redistribution per endpoint. |

MIT permits use of the software under its notice conditions; it does not grant
ownership or redistribution rights to data fetched from a third party. A later
adapter must preserve the underlying publisher, terms URL, and attribution.

## Endpoint stability and access boundary

AKShare contains many interfaces, and the project documentation notes ongoing
maintenance in response to target-page changes. Therefore:

- there is no package-wide schema or uptime guarantee;
- endpoint names, fields, request parameters, and source domains can change;
- a successful call proves only that one interface worked at one time;
- retrying a changed page with a different parser is a semantic change and needs
  review;
- arbitrary interface names/URLs must not bypass Finahinking's HTTP allowlist,
  timeout, payload, and retry limits.

An interface may be considered only with a pinned project revision, exact
function/endpoint, request parameters, source URL, response hash, and parser
version. The raw response must be captured before normalization.

## Historical values, revisions, and point-in-time controls

AKShare does not expose one global policy for release times, revisions, or
vintages. These properties depend on the underlying source and endpoint:

- a date column generally identifies an observation period, not the moment the
  value became public;
- a current web table may restate older periods without a vintage identifier;
- corporate-action and financial-statement endpoints can have source-specific
  restatement rules;
- `retrieved_at` is local observation time and cannot be substituted for
  `published_at` or `available_at`.

Until an endpoint-specific official release or provider availability contract
is proven, `available_at` remains unknown and point-in-time features/claims are
blocked. Revisions must be represented as append-only observation versions with
the source artifact and a supersession link. A returned historical date range
is not proof that historical vintages can be reconstructed.

## Grain, schema, and reconciliation

The grain is interface-specific: examples may be security/date, index/date,
financial-period/field, or another dimension set. The reviewer must specify a
logical key, units, adjustment convention, calendar/timezone, and duplicate
rule before admitting an endpoint.

Required checks include:

1. endpoint and underlying source identity;
2. schema and field-type stability;
3. missingness, placeholder values, and footnotes;
4. duplicate logical keys and pagination overlap;
5. numeric/unit validity and adjustment semantics;
6. period ordering and timezone conversion;
7. release/availability and revision evidence;
8. reconciliation against the original publisher or another admitted source.

Conflicting rows are retained as source conflicts. AKShare's own normalization
or a “latest” label does not resolve a conflict.

## Allowed and prohibited uses in P6.5

Allowed now:

- search the interface catalog to find a candidate official endpoint;
- inspect request/field mappings and understand coverage;
- use a pinned, captured response in a non-authoritative cross-check or
  prototype test, clearly labeled as AKShare/underlying-source evidence;
- compare an AKShare response to the BLS fixture only as a diagnostic, never as
  a substitute for BLS.

Prohibited now:

- direct product `FACT` claims from an AKShare response;
- treating all AKShare functions as equally admitted;
- hiding the underlying publisher or using `akshare` as the sole source ID;
- deriving `available_at` from retrieval time;
- silently switching to AKShare when BLS fails;
- using source text or repository code as authority to execute SQL, code,
  install packages, disclose credentials, or change admission tiers.

## Failure and fallback policy

| Failure | Action |
| --- | --- |
| Target page/API timeout or block | Bounded transport failure; preserve error/capture metadata and stop dependent claims. |
| Interface schema drift/removal | Quarantine and require endpoint review; do not guess field positions. |
| Missing/placeholder value | Preserve row and reason in a quality artifact; never coerce to zero. |
| Upstream source disagreement | Create a visible conflict with both source identities and captures. |
| Rate/terms/authentication failure | Do not bypass controls or rotate to an unreviewed endpoint; use only an independently admitted source. |
| BLS unavailable | Use a BLS replay fixture for deterministic audit, not AKShare as an authoritative fallback. |

## Future admission requirements

For a specific endpoint to move to `ADMIT_RESEARCH_ONLY`, the owner must
provide an admission record covering the exact upstream publisher, terms,
authentication, rate limits, stable request/response grammar, raw capture and
replay, historical/revision/PIT semantics, grain and duplicates, failure
behavior, and a bounded fallback. A move to authoritative status would require
direct admission of the original publisher or an explicit provider contract;
AKShare's wrapper status alone can never grant that authority.

## Final decision

**TIER_2 / `DISCOVERY_ONLY`.** AKShare remains a discovery and research
candidate. It is not installed, not an admitted provider, and not an
authoritative source in P6.5.

