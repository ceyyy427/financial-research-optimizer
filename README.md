# Finathink

Finathink (the Python import namespace remains `finahinking`; the distribution and CLI identity is `finathink`) is a local-first financial research laboratory for learning from
real evidence, mathematics, code, and reproducible experiments. It is a
research and education tool, not a broker, trading system, investment adviser,
or source of financial advice. Finathink provides no investment advice. The
current local source-beta line is `0.1.x`. The P8.2 product surface is
server-rendered, loopback-only, and usable offline with deterministic sample
data. Research, ML, Parameter Lab, engine, and data-source surfaces remain
read-only/sample-labelled; optional Qlib/vectorbt engines are isolated and
QMT is not connected.

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

## The Finathink loop

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

The product shell is organized around human questions: Home, Events, Explore,
Knowledge, Quant, Strategy Lab, and Workspace. The launch surface uses two
static Finathink frames with a short, reduced-motion-aware gradient transition;
the frames are brand orientation, not financial evidence.

![Finathink launch map](site/assets/finathink-splash-map.jpg)

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

The phase history is P0–P8.1; P8.2 and P8.2B are the current conditional local
checkpoints. P8.2 adds the inspectable research workspace and P8.2B adds the
structured mathematical knowledge/pedagogy layer while preserving the
research-only boundary. Current evidence is indexed in
[`docs/p8_2/P8_2_FINAL_VALIDATION_REPORT.md`](docs/p8_2/P8_2_FINAL_VALIDATION_REPORT.md).
The P8.2B gate is indexed in
[`docs/p8_2/P8_2B_FINAL_VALIDATION_REPORT.md`](docs/p8_2/P8_2B_FINAL_VALIDATION_REPORT.md).

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

The mission-specified canonical repository is
[`ceyyy427/financial-research-optimizer`](https://github.com/ceyyy427/financial-research-optimizer).
The reviewed P8.2B source is published on the non-force branch
[`codex/finathink-p82b-release`](https://github.com/ceyyy427/financial-research-optimizer/tree/codex/finathink-p82b-release).
The authenticated remote has real CI and a published `v1.3.0`, but this
checkout and that remote currently have unrelated Git histories. The branch
is therefore published without claiming that this local `0.1.x` product has
been merged into or released from canonical `main`. See
[`docs/p8_1/P8_1_HISTORY_RECONCILIATION.md`](docs/p8_1/P8_1_HISTORY_RECONCILIATION.md)
for the evidence and safe next action.

The static marketing surface is in [`site/index.html`](site/index.html). It
uses the real launch assets, links to the verified canonical repository, and
keeps GitHub release/download claims conditional until a release containing
this product is actually created.

## License

Code and documentation are released under the [MIT License](LICENSE), subject
to the attribution and third-party notices in
[the license review](docs/p8/P8_LICENSE_REVIEW.md). Bundled fixtures are
reviewed separately; their source and reuse basis are recorded in
[DATA_SOURCES.md](docs/DATA_SOURCES.md).
