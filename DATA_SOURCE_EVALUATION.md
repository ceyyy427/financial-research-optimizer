# Data Source Evaluation: ECB Data Portal

| Criterion | Assessment |
|---|---|
| Availability | Public SDMX REST endpoint; fixture-backed tests and an opt-in live smoke test. |
| License/terms | Official ECB public data; users must verify current reuse/attribution terms before redistribution. |
| Reliability | First-party central-bank source with documented SDMX schema. |
| Maintenance | Active institutional portal; schema changes remain a tracked risk. |
| Cost | No API key or paid account for the selected public series. |
| Privacy | No user data is sent; requests contain only series and date parameters. |

Selected series: ECB EXR USD/EUR reference exchange rate (`EXR.D.USD.EUR.SP00.A`).
The provider preserves the exact request URL and retrieval time as provenance.
