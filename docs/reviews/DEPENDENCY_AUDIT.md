# P4.5 Dependency Audit

**Result:** PASS for repository and virtual-environment scope, with one host
isolation note

## Evidence commands

- `.venv/bin/python --version`
- `.venv/bin/jupyter lab --version`
- `.venv/bin/pip list --format=freeze`
- `.venv/bin/pip check`
- package-metadata checks for vectorbt, Backtrader, Pyfolio Reloaded, Pyfolio,
  and Ollama
- `rg` import scans across `src/` and `tests/`
- `brew list --versions libomp`
- `command -v ollama`

## Approved environment observed

| Component | Observed version |
| --- | --- |
| Python | 3.13.7 |
| JupyterLab | 4.6.4 |
| NumPy | 2.5.3 |
| Pandas | 3.0.6 |
| Matplotlib | 3.11.2 |
| SciPy | 1.18.1 |
| scikit-learn | 1.9.1 |
| XGBoost | 3.4.1 |
| LightGBM | 4.7.0 |
| libomp | 23.1.2 |

Pytest, Ruff, and IPython/Jupyter support packages are also present. `pip check`
reported no broken requirements.

## Forbidden P5 dependencies

| Candidate | Python environment | Source/test imports | Manifest entry |
| --- | --- | --- | --- |
| vectorbt | Absent | Absent | Absent |
| Backtrader | Absent | Absent | Absent |
| Pyfolio Reloaded / Pyfolio | Absent | Absent | Absent |
| Ollama Python package | Absent | Absent | Absent |

The names appear only in design/audit documents that explicitly prohibit or
evaluate future adoption. No P5 dependency was introduced into
`pyproject.toml`, `requirements.lock`, source, or tests.

## Host isolation note

The workstation already contains `/usr/local/bin/ollama` version 0.35.0. It is
outside the project virtual environment and repository manifests, and there is
no project integration or invocation. This audit did not install or remove it.
Future work must treat it as unavailable unless a separate P7 dependency and
security gate explicitly approves it.

## Decision

The Finahinking project dependency boundary remains unchanged and free of P5/P7
candidates. **PASS**, with the host Ollama binary recorded as an external
environment fact rather than a project dependency.
