# Contributing

Contributions should improve reproducibility, source traceability, or the
clarity of the research. Read `ARCHITECTURE.md`, `DEPENDENCY_RECORD.md`, the
applicable phase gate, and the relevant contribution contract before changing
code. The project remains research-only: no brokerage, live execution,
investment advice, or required telemetry is accepted.

## Local setup

Use Python 3.11 or newer and a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
```

The optional `research` extra is only needed for notebook work. PostgreSQL is
an advanced migration-validation environment; SQLite is the default local
store. Do not commit `.env`, API keys, local databases, private research, or
generated diagnostic bundles.

## Change workflow

1. State the research question, user impact, and evidence boundary.
2. Add or update tests before implementation and run the focused test.
3. Keep network access inside allowlisted provider modules; add a reviewed,
   replayable fixture for deterministic tests.
4. Record every dependency change in `DEPENDENCY_RECORD.md` and update the
   lock file when the environment exists.
5. For schema changes, add an additive migration and test a fresh and upgrade
   database path.
6. Update the relevant architecture, evolution, limitation, and provenance
   record.
7. Run the complete checks before requesting review:

   ```bash
   python -m pytest -q
   ruff check src tests scripts
   python scripts/validate_governance.py .
   python -m pip check
   python -m jupyter nbconvert --to notebook --execute --output /tmp/finahinking_research_workflow_executed.ipynb notebooks/01_research_workflow.ipynb
   git diff --check
   ```

8. Ask an independent reviewer to check phase gates, research validity,
   privacy, and security. Keep commits focused and reproducible.

## Contribution contracts

- Knowledge: [KNOWLEDGE_CONTRIBUTION.md](docs/KNOWLEDGE_CONTRIBUTION.md)
- Data adapters: [DATA_ADAPTER_CONTRIBUTION.md](docs/DATA_ADAPTER_CONTRIBUTION.md)
- Features: [FEATURE_CONTRIBUTION.md](docs/FEATURE_CONTRIBUTION.md)
- Strategy research: [STRATEGY_RESEARCH_GUIDE.md](docs/STRATEGY_RESEARCH_GUIDE.md)

Every knowledge entry needs typed content, prerequisites, source references,
and a learning/application explanation. New data sources require license,
temporal semantics, provenance, capture/replay, and tests. Quant features
require a formula, timing/availability contract, lineage, and learning
explanation. AI-assisted drafts must be reviewed by a human before they can
be authoritative.

## Pull requests

Use a small, descriptive title and include: scope, tests, data/knowledge
sources, migration or dependency impact, security/privacy impact, and known
limitations. Research-correctness changes should include a before/after
example and identify look-ahead, survivorship, revision, or multiple-testing
risks. Do not claim a release, benchmark, or external source validation that
was not actually run.
