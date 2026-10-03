# Finahinking

Finahinking is a local-first financial research laboratory for learning from
real evidence, mathematics, code, and reproducible experiments. It is a
research and education tool, not a broker, trading system, investment adviser,
or source of financial advice. Finahinking provides no investment advice. The
current public-beta line is `0.1.x`.

What it is:

- a Knowledge Engine that connects intuition, equations, derivations, code,
  financial interpretation, and quant/strategy applications;
- a captured-data event workflow (the initial CPI journey uses a reviewed BLS
  fixture and needs no credential);
- a deterministic quant and research-only Strategy Lab with OOS and paper
  simulation boundaries;
- private personal continuity and evidence-linked community projections.

What it is not: a promise of alpha, an autonomous stock picker, a real-money
execution path, a substitute for professional advice, or a hosted account
service. Real-money trading, broker credentials, cloud accounts, and required
telemetry are explicitly out of scope.

## The Finahinking loop

```text
REAL EVENT → EVIDENCE → UNDERSTANDING → MATHEMATICS → CODE
→ QUANT RESEARCH → STRATEGY RESEARCH → BACKTEST → OOS → PAPER
→ LEARNING → PERSONAL KNOWLEDGE → COMMUNITY → NEW QUESTIONS
```

Two supported learning loops are:

```text
REAL EVENT → EVIDENCE → UNDERSTANDING → LEARNING
IDEA → FEATURE → MATH → CODE → BACKTEST → PAPER → LEARNING
```

## First run (source install)

Python 3.11+ is required. The deterministic path is deliberately useful
without a market-data key:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m pytest -q
python scripts/run_local_app.py --sample --port 8765
```

Open `http://127.0.0.1:8765/`. Select the captured BLS CPI event, open its
linked concept, run the deterministic quant example, and save the learning
state. The app is local-first; outbound source calls are opt-in and bounded.
See [Quickstart](docs/QUICKSTART.md), [Installation](docs/INSTALLATION.md),
and [Known Limitations](docs/KNOWN_LIMITATIONS.md).

## Repository map

- `src/finahinking/` — the Python package and stable module boundaries.
- `fixtures/` — deterministic, reviewed input data for tests and sample mode.
- `tests/` — unit, integration, gate, and documentation checks.
- `migrations/` — additive SQLite/PostgreSQL-compatible schema changes.
- `docs/` — phase contracts, tutorials, and validation evidence.
- `.github/` — CI, release workflow, issue forms, and security automation.

The phase history is P0–P7.5; P8 makes the source distribution public-beta
ready without changing the research-only boundary. The current gate evidence
is in `docs/p8/P8_PUBLIC_BETA_GATE.md` and
`docs/p8/P8_FINAL_VALIDATION_REPORT.md`.

## Development and contribution

```bash
python scripts/validate_governance.py .
python -m pytest -q
ruff check src tests scripts
python -m pip check
git diff --check
```

Read [Contributing](CONTRIBUTING.md), the [Strategy Research Guide](docs/STRATEGY_RESEARCH_GUIDE.md),
and the contribution contracts for [knowledge](docs/KNOWLEDGE_CONTRIBUTION.md),
[data adapters](docs/DATA_ADAPTER_CONTRIBUTION.md), and [features](docs/FEATURE_CONTRIBUTION.md).
The authoritative state record remains [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md).

## Distribution and website

The canonical public distribution is the GitHub Releases page for this
repository once a maintainer publishes a signed `v0.x.y` tag. The repository
currently contains the reproducible source-install and release workflow; no
release asset is claimed until that external publication exists. A future
`finathink.cloud` marketing/docs surface should link to that page rather than
duplicating version strings. Suggested copy is “Understand finance by
thinking with data.” See the [finathink.cloud content contract](docs/FINATHINK_CLOUD.md).

## License

Code and documentation are released under the [MIT License](LICENSE), subject
to the attribution and third-party notices in
[the license review](docs/p8/P8_LICENSE_REVIEW.md). Bundled fixtures are
reviewed separately; their source and reuse basis are recorded in
[DATA_SOURCES.md](docs/DATA_SOURCES.md).
