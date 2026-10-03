# P8 public-beta gate

This checklist is the evidence index for the 47-item mission gate. “Ready”
means the repository contains a reproducible check; “external” means a
maintainer must publish/run it on the remote and cannot be honestly simulated
in this checkout.

| # | Gate item | Evidence/status |
|---:|---|---|
| 1 | P7.5 gate | See `docs/p7_5/P7_5_FINAL_VALIDATION_REPORT.md` — PASS |
| 2–5 | License and data rights | `P8_LICENSE_REVIEW.md`, `docs/DATA_SOURCES.md` — PASS for current source tree |
| 6–11 | README, quickstart, install, CPI/quant/strategy tutorials | Root README and `docs/QUICKSTART.md`, `docs/INSTALLATION.md`, `docs/STRATEGY_RESEARCH_GUIDE.md` — PASS |
| 12 | Clean install | Fresh temporary venv install, docs tests, smoke, and pip check — PASS |
| 13 | macOS Apple Silicon package if selected | Source-only beta; not selected |
| 14–20 | Artifact launch, sample, knowledge, quant, strategy, persistence, restart | Local app HTTP probe, 11 P7.5 tests, temp SQLite save/reopen — PASS |
| 21 | Research provenance | P6.5/P7 provenance contracts, catalog fingerprint, data source register — PASS |
| 22–24 | Security, secret, dependency review | `P8_SECURITY_REVIEW.md`, secret scan, both `pip check` runs — PASS |
| 25–26 | GitHub CI and release workflow | `.github/workflows/ci.yml`, `release.yml` committed; remote execution — EXTERNAL |
| 27–29 | Contribution guides | Three contract docs and issue forms — PASS |
| 30–35 | Privacy, network, telemetry, limits, no real-money, website target | `docs/PRIVACY.md`, `docs/KNOWN_LIMITATIONS.md`, README — PASS; release URL conditional |
| 36 | GitHub release assets/download path | No remote/release exists in checkout — EXTERNAL |
| 37 | Contributor setup | `CONTRIBUTING.md` and issue templates — PASS |
| 38–44 | Full tests, Ruff, notebook, governance, migration, dependency, build | `make p5-5-gate`, Postgres check, wheel, and 260/1 suites — PASS |
| 45–46 | Diff check and clean worktree | final delivery commit, `git diff --check`, clean status — PASS |
| 47 | Known release commit/tag | No tag created by this task — External publish required |

## Decision

The source-distribution/public-beta preparation is complete. The overall P8
gate is **CONDITIONAL** until P7.5 evidence is attached and a maintainer runs
CI and publishes a real GitHub release/tag. This document intentionally does
not invent an external URL, asset checksum, or release status.
