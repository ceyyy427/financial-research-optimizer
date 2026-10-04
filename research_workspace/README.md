# Research workspace

This directory is the home for local, reproducible research notebooks. The
starter workflow in [`notebooks/01_research_workflow.ipynb`](../notebooks/01_research_workflow.ipynb)
uses a fixed random seed and generated prices, so it runs without network
access or credentials.

## Recreate the environment

From the repository root, create or refresh the virtual environment and run
the P1 checks:

```bash
python3.11 -m venv .venv
make install
make p1-gate
```

The package is intentionally a research library. Notebook work should record
the data source, retrieval date, transformations, and known limitations before
any result is used in a decision.

## Notebook conventions

- Keep examples deterministic by setting an explicit seed.
- Prefer recorded fixtures for provider work; do not require live network
  access in the default test or notebook path.
- Keep exploratory outputs separate from source modules and avoid committing
  secrets, personal data, or trading instructions.
