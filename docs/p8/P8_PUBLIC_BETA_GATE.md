# P8 public-beta gate

This checklist is the evidence index for the 47-item mission gate. “Ready”
means the repository contains a reproducible check; “external” means a
maintainer must publish/run it on the remote and cannot be honestly simulated
in this checkout.

| # | Gate item | Evidence/status |
|---:|---|---|
| 1 | P7.5 gate | See `docs/p7_5/P7_5_FINAL_VALIDATION_REPORT.md`; parent gate |
| 2–5 | License and data rights | `P8_LICENSE_REVIEW.md`, `docs/DATA_SOURCES.md` — Ready |
| 6–11 | README, quickstart, install, CPI/quant/strategy tutorials | Root README and `docs/QUICKSTART.md`, `docs/INSTALLATION.md`, `docs/STRATEGY_RESEARCH_GUIDE.md` — Ready |
| 12 | Clean install | `P8_CLEAN_INSTALL_REPORT.md` and CI job — Ready to run |
| 13 | macOS Apple Silicon package if selected | Source-only beta; not selected |
| 14–20 | Artifact launch, sample, knowledge, quant, strategy, persistence, restart | Local app/tests and P7.5 report — Verify at parent gate |
| 21 | Research provenance | P6.5/P7 provenance contracts and data source register — Ready |
| 22–24 | Security, secret, dependency review | `P8_SECURITY_REVIEW.md`, CI scans, `pip check` — Ready to run |
| 25–26 | GitHub CI and release workflow | `.github/workflows/ci.yml`, `release.yml` — External run required |
| 27–29 | Contribution guides | Three contract docs — Ready |
| 30–35 | Privacy, network, telemetry, limits, no real-money, website target | `docs/PRIVACY.md`, `docs/KNOWN_LIMITATIONS.md`, README — Ready; URL pending release |
| 36 | GitHub release assets/download path | No remote/release exists in checkout — External publish required |
| 37 | Contributor setup | `CONTRIBUTING.md` and issue templates — Ready |
| 38–44 | Full tests, Ruff, notebook, governance, migration, dependency, build | Existing phase gates + CI workflow — Run on final commit |
| 45–46 | Diff check and clean worktree | Maintainer final gate — Required |
| 47 | Known release commit/tag | No tag created by this task — External publish required |

## Decision

The source-distribution/public-beta preparation is complete. The overall P8
gate is **CONDITIONAL** until P7.5 evidence is attached and a maintainer runs
CI and publishes a real GitHub release/tag. This document intentionally does
not invent an external URL, asset checksum, or release status.
