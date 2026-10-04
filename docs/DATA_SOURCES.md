# Data sources and fixture register

Every source is admitted with provenance, temporal semantics, reuse basis, and
a replayable capture where practical. `LIVE` means an explicit network read;
`CAPTURED` is a reviewed source payload stored for replay; `SAMPLE` is a
deterministic teaching fixture; `CACHED` is a user-local prior result. Labels
must not be silently changed after a transport failure.

| Source/fixture | Label | Purpose | Rights/reuse basis | Limitations |
| --- | --- | --- | --- | --- |
| U.S. Bureau of Labor Statistics CPI API (`https://api.bls.gov/publicAPI/v2/timeseries/data/`) | CAPTURED / LIVE (opt-in) | CPI event learning | Public government endpoint; follow current BLS terms and attribution | Revisions, unavailable periods, and API limits apply; not a tick feed |
| `fixtures/p6_5/bls_cpi_2024_2025.json` | CAPTURED | Offline CPI tutorial and tests | BLS Public Data API v2 response captured 2025-01-15T13:32:00Z; SHA-256 `8605d29086e5856d61947f3540202a6b3d8644b0cb08098d3c6cfa3fe6e1108e`; U.S. government source attribution and current BLS terms apply | Historical capture, not a live quote; preserve the capture timestamp/hash when redistributing |
| `fixtures/p4_5/volatility_workflow.csv` | SAMPLE | Deterministic volatility examples | Project-authored fixture | Synthetic/teaching data |
| `fixtures/p5_5/*.csv` | SAMPLE | Quant and OOS tests | Project-authored deterministic fixtures | Not investable market history |
| `fixtures/ecb/exchange_rate_usd_eur.csv` | SAMPLE | FX feature tests | Fixture provenance is recorded in source tests | Limited rows; no current FX claim |

New sources must add a row, capture metadata, source terms, temporal semantics,
and tests. Proprietary or unclear-rights data must not be bundled. See
[DATA_ADAPTER_CONTRIBUTION.md](DATA_ADAPTER_CONTRIBUTION.md).
