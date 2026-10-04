# P8 public-beta gate

This checklist is the evidence index for the 47-item mission gate. “Ready”
means the repository contains a reproducible check; “external” means a
maintainer must publish/run it on the remote and cannot be honestly simulated
in this checkout.

| # | Gate item | Evidence/status |
|---:|---|---|
| 1 | P7.5 gate | See `docs/p7_5/P7_5_FINAL_VALIDATION_REPORT.md` — PASS for bounded local product slice |
| 2–5 | License and data rights | `P8_LICENSE_REVIEW.md`, `docs/DATA_SOURCES.md` — PASS for current source tree |
| 6–11 | README, quickstart, install, CPI/quant/strategy tutorials | Root README and `docs/QUICKSTART.md`, `docs/INSTALLATION.md`, `docs/STRATEGY_RESEARCH_GUIDE.md` — PASS |
| 12 | Clean install | Fresh temporary venv installs the wheel outside the source checkout; migration, captured event, quant POST, and strategy contract smoke — PASS |
| 13 | macOS Apple Silicon package if selected | Source-only beta; not selected |
| 14–20 | Artifact launch, sample, knowledge, quant, strategy, persistence, restart | `scripts/clean_install.py`, `tests/validation/test_artifact_install.py`, product gate tests, temp SQLite save/reopen — PASS |
| 21 | Research provenance | P6.5/P7 provenance contracts, catalog fingerprint, data source register — PASS |
| 22–24 | Security, secret, dependency review | Loopback/CSRF/CSP controls, secret scan, `pip check`, CI/release `pip-audit --strict` workflow — PASS locally; advisory scan requires installed service/CI run |
| 25–26 | GitHub CI and release workflow | `.github/workflows/ci.yml`, `release.yml` committed; remote execution — EXTERNAL |
| 27–29 | Contribution guides | Three contract docs and issue forms — PASS |
| 30–35 | Privacy, network, telemetry, limits, no real-money, website target | `docs/PRIVACY.md`, `docs/KNOWN_LIMITATIONS.md`, README, and `site/index.html` — PASS for local/static surface; release URL conditional |
| 36 | GitHub release assets/download path | No remote/release exists in checkout — EXTERNAL |
| 37 | Contributor setup | `CONTRIBUTING.md` and issue templates — PASS |
| 38–44 | Full tests, Ruff, notebook, governance, migration, dependency, build | 268 passed/1 skipped, Ruff, notebook, governance, wheel clean-install, and migration checks — PASS |
| 45–46 | Diff check and clean worktree | `git diff --check`; clean status at local release tag `v0.1.0` — PASS |
| 47 | Known release commit/tag | Local annotated tag `v0.1.0` points at the delivery commit and passes `prepare_release.py --check --tag`; GitHub publication remains external |

## Decision

The source-distribution/public-beta preparation is complete for the local
artifact and static marketing surface. The overall P8 gate is **CONDITIONAL**
until a maintainer runs the GitHub workflows and publishes a real release/tag;
this checkout has no configured remote and does not invent an external URL,
asset checksum, or release status.
