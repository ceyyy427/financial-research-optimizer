PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff

.PHONY: install test lint notebook-check p1-gate

install:
	$(PIP) install --requirement requirements.lock
	$(PIP) install --editable '.[dev,research]'

test:
	$(PYTEST) -q

lint:
	$(RUFF) check src/finahinking/__init__.py tests/test_environment.py

notebook-check:
	$(PYTHON) -m jupyter nbconvert --to notebook --execute --inplace notebooks/01_research_workflow.ipynb

p1-gate: test lint notebook-check
	@echo 'P1 gate checks passed'
