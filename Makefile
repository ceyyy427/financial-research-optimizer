PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff

.PHONY: install test lint notebook-check p1-gate p5-5-gate

install:
	$(PIP) install --requirement requirements.lock
	$(PIP) install --editable '.[dev,research]'

test:
	$(PYTEST) -q

lint:
	$(RUFF) check src tests scripts

notebook-check:
	$(PYTHON) -m jupyter nbconvert --to notebook --execute --output /tmp/finahinking_research_workflow_executed.ipynb notebooks/01_research_workflow.ipynb

p1-gate: test lint notebook-check
	@echo 'P1 gate checks passed'

p5-5-gate: p1-gate
	$(PYTHON) scripts/validate_governance.py .
	$(PIP) check
	.venv-quant/bin/pip check
	PYTHONPATH=src .venv-quant/bin/python -c "import pandas as pd; from finahinking.quant.adapters.statsmodels_adapter import StatsmodelsAdapter; print(StatsmodelsAdapter().fit_ols(pd.DataFrame({'y':[1.,2.,3.], 'x':[0.,1.,2.]}), 'y', ['x']).fingerprint)"
	@echo 'P5.5 gate command set passed'
