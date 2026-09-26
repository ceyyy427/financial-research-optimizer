# Source Adapter Contract

`config/source_registry.yaml` is the executable registry for public, licensed, secondary, and library-backed financial sources. A source profile is not a URL list: it declares authority, access methods, authorization, point-in-time and revision capabilities, parser/normalizer versions, required fields, and quality checks.

## Routing order

The router scores candidates in this order:

1. declared authority and source priority;
2. required point-in-time, vintage, release, and revision capabilities;
3. required-field coverage;
4. freshness and stability;
5. authorization status and access cost.

The access method order is API, official download, authorized database, Patchright browser, CDP capture, DOM parsing, and valid cached snapshot. A secondary aggregator cannot become the sole primary source for a `research_grade` or `portfolio_grade` run when an official or authorized source is available.

```python
from scripts.source_router import SourceRouter

router = SourceRouter.from_file("config/source_registry.yaml")
plan = router.resolve(
    topic="美国 CPI 历史修订值",
    universe=["CPIAUCSL"],
    required_capabilities=["point_in_time", "vintage_data"],
)
```

The returned plan contains `source_plan`, `fallback_plan`, and `blocking_rules`. Material price conflicts, missing effective timestamps, unknown adjustment conventions, expired authorization, and unavailable point-in-time fields stop dependent model analysis.

## Source classes

- Official exchanges, regulators, central banks, and statistics agencies are preferred for primary evidence.
- FRED and ALFRED are distinct logical sources: FRED is current visible history; ALFRED is vintage-aware history for a historical information set.
- Eastmoney, 10jqka, Yahoo Finance, Investing.com, and TradingView are secondary sources for discovery or cross-checking, not an unqualified authority.
- Wind, CSMAR, Nasdaq Data Link, and JoinQuant require licensed or user-authorized inputs. The skill supports authorized APIs, database snapshots, CSV, and Excel imports; it does not scrape licensed services.
- AkShare and Tushare are library adapters. Provenance must record their underlying source rather than treating the library name as the data authority.

## Required handoff

Every adapter must emit an immutable source snapshot before normalization. Every normalized row must satisfy `schemas/canonical_observation.schema.json` and retain `observation_time`, `release_time`, `availability_time`, `effective_time`, and `vintage_time` (with an explicit `null`/`not_available` status when a source cannot provide one). Canonical observations are the only records eligible for feature construction.
