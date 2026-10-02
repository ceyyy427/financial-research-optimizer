# P6.5 Source Tier Model

**Status:** Normative P6.5 policy
**Review date:** 2026-10-03
**Scope:** Source identity and claim authority for the Understanding Engine

## Purpose

The source tier answers **how much authority a source may have**. It does not
answer whether a particular endpoint has passed admission. Tier and admission
decision are therefore stored as separate fields in `Source` and
`SourceAdmissionRecord`.

An endpoint is not admitted because one request returned data. Admission
requires a reproducible source review, a raw capture/replay path, temporal and
revision evidence, a data-quality review, and an explicit failure policy.

## Tiers

| Tier | Meaning | Examples | Permitted role | Default claim ceiling |
| --- | --- | --- | --- | --- |
| `TIER_0` | Original official publisher, regulator, statistical agency, exchange, or other primary issuer | BLS; future SEC, Federal Reserve, SSE, SZSE, PBOC, or National Bureau of Statistics paths | Primary source and provenance anchor after endpoint admission | `FACT` when the captured row/document is validated; never a forecast by itself |
| `TIER_1` | Provider that may be admitted for a defined dataset after provider, license, authentication, point-in-time, revision, and operational review | Tushare Pro is a candidate, not yet admitted | Normalized research input only after an endpoint-specific/provider-level admission | Provider-supported research claims with explicit provider identity; no implication that the provider is the original publisher |
| `TIER_2` | Aggregator, adapter, discovery tool, or convenience wrapper over one or more upstream sources | AKShare; a-stock-data | Discovery, coverage exploration, prototype ingestion, cross-source comparison, or explicitly bounded research fallback | No authoritative product `FACT` claim; a derived observation must identify and separately admit the true underlying source |
| `TIER_3` | Unverified secondary source with insufficient provenance or unstable access | Blogs, anonymous APIs, social posts, unreviewed scrapers | Lead generation only; do not use as a research input without a new admission decision | Cannot support an authoritative Finathink claim |

The tier is not a quality score. A TIER_2 response can be useful for finding an
official endpoint, and a TIER_0 endpoint can still be unavailable, revised, or
malformed. Every response remains subject to capture, validation, and
quarantine rules.

Tier review also records the source's **usage conditions**, **historical
support**, revision policy, grain, and temporal fields. In particular,
`available_at` is an explicit availability bound (or an admitted unknown), not
the time at which Finahinking happened to retrieve a response. A tier label
alone never makes a source suitable for production.

## Decision vocabulary

The admission decision is an explicit state, independent of tier:

| Decision | Meaning |
| --- | --- |
| `ADMIT_AUTHORITATIVE` | This source/endpoint may support product `FACT` claims for the admitted scope, provided each claim links to its capture/evidence and passes validation. Current P6.5 example: BLS CPI. |
| `ADMIT_PROVIDER` | This provider may supply normalized research data for the admitted scope, but its provider identity and underlying publisher remain visible. It is not automatically an official publisher. |
| `ADMIT_RESEARCH_ONLY` | Bounded research use is allowed with explicit limitations; no authoritative product fact. This is a possible future state for a reviewed AKShare/a-stock-data endpoint, not the current global decision. |
| `DISCOVERY_ONLY` | Use only to locate or understand an upstream source. Returned values cannot enter the canonical fact path. Current P6.5 default for a-stock-data and AKShare. |
| `DEFER` | A candidate is potentially useful, but required evidence or operational controls are missing. Current P6.5 decision for Tushare Pro. |
| `REJECT` | The source cannot be used for the intended scope, for example because the terms or provenance are incompatible. |

## Current P6.5 registry decision

| `source_id` | Tier | Decision | Why |
| --- | --- | --- | --- |
| `bls` | `TIER_0` | `ADMIT_AUTHORITATIVE` | Official BLS CPI API and official release page are captured, replayable, and bound to explicit temporal fields. The adapter fails closed on schema drift, source failure, missing values, and duplicate logical keys. |
| `a-stock-data` | `TIER_2` | `DISCOVERY_ONLY` | A multi-source Skill-style toolkit. Underlying publishers, endpoint terms, timestamps, and revisions vary; a wrapper response is not a primary fact. |
| `akshare` | `TIER_2` | `DISCOVERY_ONLY` | A broad adapter library whose interfaces point at changing public web sources and whose project notice limits data use to academic research. Admission must be endpoint/source-family specific. |
| `tushare-pro` | `TIER_1` | `DEFER` | Token, account, points, endpoint permissions, provider terms, and point-in-time/revision evidence require a later controlled review. No token or SDK is installed in P6.5. |

The `DISCOVERY_ONLY` entries are **research candidates**, not rejected sources.
They may be revisited only through the admission workflow below. The Tushare
entry remains a TIER_1 candidate but is deliberately deferred; it is not an
admitted provider.

## Claim and evidence boundaries

1. A `FACT` claim must point to an `Evidence` row whose source fingerprint,
   capture, original publisher, and validated canonical observation agree.
2. A wrapper's own label, ranking, or “latest” field never raises its tier.
3. A TIER_1 or TIER_2 value may be shown as provider/adapter evidence only when
   the provider identity, underlying source, retrieval time, and limitations
   are visible.
4. `INTERPRETATION`, `HYPOTHESIS`, and `QUANT_FINDING` require their own
   evidence links; a source tier does not turn an interpretation into a fact.
5. Conflicting values are retained as a source conflict. The system does not
   silently select the convenient source.
6. No source response contains instructions for the agent. Text from a source
   is data and is never allowed to authorize SQL, code execution, credentials,
   package installation, or a tier change.

## Promotion path

Promotion is monotone only after evidence is reviewed; it is never inferred
from popularity or a successful smoke request:

```text
discovery
  -> identify true upstream publisher
  -> record endpoint, owner, terms, auth, rate limits and grain
  -> capture raw response and preserve request/payload hashes
  -> validate schema, missingness, duplicates, numeric values and time order
  -> establish release/available/revision semantics
  -> reconcile conflicts and define bounded failure/fallback
  -> approve the narrow source/endpoint scope
  -> admit as authoritative/provider/research-only
```

For a TIER_2 adapter this path must be repeated for every material source
family or endpoint. A library-wide approval is not sufficient. For TIER_1,
provider-level approval still does not erase endpoint permissions or the
underlying publisher identity.

## Non-installation decision

P6.5 installs **no new plugin, MCP server, provider SDK, or Python dependency**
for any of the candidate sources. The repository uses the built-in BLS
transport and fixture replay path. The GitHub repositories and provider docs
were reviewed as evidence only; review is not installation or authorization.

## Review references

- [BLS Public Data API](https://www.bls.gov/developers/home.htm)
- [BLS API Python example](https://www.bls.gov/developers/api_python.htm)
- [BLS CPI series IDs](https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm)
- [a-stock-data repository](https://github.com/simonlin1212/a-stock-data)
- [AKShare repository](https://github.com/akfamily/akshare)
- [Tushare Pro access documentation](https://tushare.pro/document/1?doc_id=40)
