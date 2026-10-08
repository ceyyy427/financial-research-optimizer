# Task 6 report

Implemented bounded factor parameter experiments and decay ranking.

- Added `FactorExperimentSpec`, finite grid expansion with `max_experiments`, and deterministic `FactorExperimentResult`/record contracts.
- Reused the existing leakage-aware factor evaluator for T+1 PIT validation evidence, explicit train/validation/test split metadata, IC/IR/turnover and decay horizons; OOS remains hidden until a frozen test evaluation.
- Bound every experiment and aggregate digest to dataset, config, and research fingerprints; retained paper-only limitations and no trade advice.
- Added `FactorResearchPipeline.run_experiments`, public research exports, HTML quant-section rendering, and descriptive comparison payload support.

Validation:

- `PYTHONPATH=src python3 -m pytest -q tests/research/test_factor_experiments.py tests/research/test_factor_pipeline.py tests/research/test_reports.py` — 12 passed.
- `PYTHONPATH=src python3 -m pytest -q` — 829 passed, 1 skipped; one pre-existing wheel-install integration failure in `tests/validation/test_artifact_install.py::test_wheel_install_exposes_migrations_fixtures_and_local_routes`.
- `PYTHONPATH=src python3 -m ruff check src/finahinking/research/factor_experiments.py src/finahinking/research/factor_pipeline.py src/finahinking/research/reports.py tests/research/test_factor_experiments.py` — passed.
