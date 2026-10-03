# P8 final validation report

## Scope

This report records the local source-distribution work for Open Source Public
Beta. It stops before cloud sync, hosted accounts, broker integration,
real-money execution, major provider expansion, and production cloud
infrastructure.

## Evidence index

- Public entry point: root `README.md`; onboarding: `docs/GETTING_STARTED.md`,
  `docs/QUICKSTART.md`, `docs/INSTALLATION.md`.
- Research/data contracts: `docs/DATA_SOURCES.md`,
  `docs/STRATEGY_RESEARCH_GUIDE.md`, and the three contribution guides.
- Safety: `SECURITY.md`, `docs/PRIVACY.md`, `docs/KNOWN_LIMITATIONS.md`,
  `docs/p8/P8_SECURITY_REVIEW.md`.
- Engineering: `.github/workflows/ci.yml`, `.github/workflows/release.yml`,
  issue templates, and `docs/p8/P8_CLEAN_INSTALL_REPORT.md`.
- Gate: `docs/p8/P8_PUBLIC_BETA_GATE.md`.

## Results

| Area | Result |
| --- | --- |
| Source install and deterministic sample path | Implemented/documented; run on final commit |
| License and source/fixture rights | Reviewed for current tree; recheck on release asset changes |
| Security/privacy/telemetry boundary | Documented; no broker or real-money path |
| CI/release workflow | Definitions committed; remote execution required |
| Native macOS package | Not selected; no unsupported binary claim |
| GitHub release/tag | Not created by this task; maintainer action required |

## Local evidence captured 2026-10-03

- `.venv/bin/pytest -q`: **268 passed, 1 skipped**.
- `ruff check src tests scripts`: passed.
- `tests/validation/test_p8_docs.py`: **3 passed**.
- `scripts/prepare_release.py --check` and `scripts/secret_scan.py`: passed.
- `scripts/run_local_app.py --sample --port 18765 --smoke`: passed.
- Loopback HTTP probe returned 200 for home, event, knowledge, quant,
  strategy, personal, community, diagnostics, health, and knowledge API
  routes. Product-gate tests also exercise event-learning ingestion,
  catalog-keyed mastery, deterministic OLS, strategy OOS/paper/compare,
  explicit community projection, and a temp SQLite save/reopen probe.
- Fresh temporary virtual environment installed the built wheel outside the
  source tree; migrations, bundled fixture, captured event, quant artifact,
  and strategy paper boundary all passed `scripts/clean_install.py`.
- `pip wheel --no-deps .`: `finahinking-0.1.0-py3-none-any.whl`; checksum is
  generated at release time and is intentionally not presented as a public
  asset until a tag exists.
- `git diff --check`: passed; the final release commit/tag remains an
  external maintainer action.
- `pip-audit -r requirements.lock --strict`: **No known vulnerabilities
  found** after the setuptools 84.0.0 pin refresh.

## Stop condition

Stop after the P8 Public Beta Gate review. Any decision to add cloud
synchronization, hosted accounts, broker execution, or production-scale
infrastructure requires real public-beta evidence and a new phase review.
