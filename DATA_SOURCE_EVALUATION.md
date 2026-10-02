# Data Source Evaluation: ECB Data Portal

| Criterion | Assessment |
|---|---|
| Availability | Public SDMX REST endpoint; fixture-backed tests and an opt-in live smoke test. |
| License/terms | ECB's current ESCB statistics reuse policy permits free reuse when the ECB is cited as source and statistics/metadata are not modified; third-party series and provider disclaimers remain subject to their own terms. See [ECB reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.ga.html) and [ECB disclaimer/copyright](https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html). |
| Reliability | First-party central-bank source with documented SDMX schema. |
| Maintenance | Active institutional portal; schema changes remain a tracked risk. |
| Cost | No API key or paid account for the selected public series. |
| Privacy | No user data is sent; requests contain only series and date parameters. |

Selected series: ECB EXR USD/EUR reference exchange rate (`EXR.D.USD.EUR.SP00.A`).
The provider preserves the exact request URL and retrieval time as provenance.
