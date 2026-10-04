# P5 Open-Source Component Admission Matrix

**Review date:** 2026-10-02

**Decision:** The P5 core runtime is the in-house deterministic engine. The
external projects below are reviewed candidates; none is installed in the
Finahinking project runtime. `statsmodels==0.15.0` is admitted only in the
isolated `.venv-quant` adapter sandbox documented separately.

## Classification key

- **A — CORE CANDIDATE:** eligible for a future default dependency after a
  separately approved installation and benchmark.
- **B — OPTIONAL ADAPTER:** may be selected by a user behind an adapter; never
  part of the domain model or required for the offline gate.
- **C — REFERENCE ONLY:** architecture or workflow reference; not imported or
  installed.
- **D — REJECTED:** not admitted to the default runtime because the license,
  maintenance, security, or architecture risk is unacceptable.

## Candidate review

| Component | Repository | License observed | Role | Classification | Compatibility / security / maintenance review | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| In-house engine | This repository | Project license | Backtest and evaluation core | **A — CORE CANDIDATE** | Python 3.11+, NumPy/Pandas, macOS arm64 friendly, no network or code execution | **Admit as P5 core** |
| statsmodels | https://github.com/statsmodels/statsmodels | Modified BSD / BSD-3-Clause | OLS, factor regression, attribution | **B — OPTIONAL ADAPTER** | Mature statistical scope and active upstream; CPython 3.13/macOS arm64 wheel and dependency tree validated in isolated sandbox; adapter only | **Admitted as isolated optional adapter (`statsmodels==0.15.0`); not a core dependency** |
| PyPortfolioOpt | https://github.com/PyPortfolio/PyPortfolioOpt | MIT | Efficient frontier, Black-Litterman, HRP | **B — OPTIONAL ADAPTER** | Depends on optimization stack and numerical versions; allocation outputs must be normalized into domain weights; no recommendation language | **Optional; not installed** |
| Alphalens Reloaded | https://github.com/stefan-jansen/alphalens-reloaded | Apache-2.0 | Factor returns, IC, turnover, tear sheets | **B — OPTIONAL ADAPTER** | Overlaps with the existing Factor Engine; upstream dependency chain includes plotting/statistics packages; compare semantics before adoption | **Optional; not installed** |
| Pyfolio Reloaded | https://github.com/stefan-jansen/pyfolio-reloaded | Apache-2.0 (verify at install time) | Portfolio performance/risk reports | **B — OPTIONAL ADAPTER** | Reporting only, not execution; dependency freshness and notebook compatibility require isolated benchmark | **Optional; not installed** |
| QuantStats | https://github.com/ranaroussi/quantstats | Apache-2.0 | Portfolio analytics and reports | **B — OPTIONAL ADAPTER** | Similar reporting surface to Pyfolio; choose one adapter, do not make both defaults; optional plotting/network helpers remain disabled | **Optional; not installed** |
| bt | https://github.com/pmorissette/bt | MIT (verify release) | Portfolio backtest candidate | **B — OPTIONAL ADAPTER** | Stateful semantics require comparison against the explicit P5 ledger; macOS arm64 and dependency tree require isolated benchmark | **Optional; not installed** |
| vectorbt | https://github.com/polakowo/vectorbt | Apache-2.0 + Commons Clause | Vectorized research adapter | **B — OPTIONAL ADAPTER** | Commons Clause creates distribution/commercial risk; never a core dependency or domain object; license gate required | **Research-only candidate; not installed** |
| Riskfolio-Lib | https://github.com/dcajasn/Riskfolio-Lib | BSD-3-Clause (verify release) | CVaR, risk parity, risk contribution | **B — OPTIONAL ADAPTER** | Advanced solver dependency and numerical reproducibility require isolated benchmark; return plain weights/metrics only | **Optional; not installed** |
| TA-Lib | https://github.com/TA-Lib/ta-lib-python | BSD-2-Clause (verify release) | Technical indicators | **B — OPTIONAL ADAPTER** | Native TA-Lib library/build tooling is a macOS arm64 risk; indicators belong in the Factor/Feature layer, not the engine core | **Optional; not installed** |
| QuantLab | https://github.com/saurabh9gupta/QuantLab | Review current upstream terms before use | Walk-forward and attribution patterns | **C — REFERENCE ONLY** | Architecture ideas only; no dependency or code import | **Reference only** |
| kuant-core | https://github.com/zwmjj/kuant-core | Review current upstream terms before use | Factor/risk/cost patterns | **C — REFERENCE ONLY** | Architecture ideas only; no dependency or code import | **Reference only** |
| Microsoft Qlib | https://github.com/microsoft/qlib | MIT (verify release) | ML research workflow | **C — REFERENCE ONLY** | Broad runtime and data assumptions exceed P5; no dependency or code import | **Reference only** |
| LEAN | https://github.com/QuantConnect/Lean | Apache-2.0 | Event-driven execution architecture | **C — REFERENCE ONLY** | Execution-oriented system is outside the research-only core; no dependency or code import | **Reference only** |
| Backtrader | https://github.com/mementum/backtrader | GPL-3.0 | Event-driven backtesting | **D — REJECTED** | GPL-3.0 is not accepted as a default project dependency; stateful semantics also weaken the explicit ledger boundary | **Reject default** |

## Admission rules

Each future installation must repeat repository, README, license, release,
issue, maintenance, and **Security** review; confirm Python/macOS arm64 support;
install only in an isolated environment; run `pip check`, tests, and a fixture
benchmark; record the exact version and dependency tree; and expose only
normalized data through an adapter. No third-party object may become a
Finahinking domain object.
