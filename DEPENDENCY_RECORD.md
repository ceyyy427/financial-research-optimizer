# Dependency Record

This file is the authoritative record of why each third-party dependency is
present, who owns it, and which project phase first needs it. No dependency is
installed without an entry here. Versions are pinned in `requirements.lock`
when the P1 environment is created.

## P0 baseline

P0 uses only the Python standard library for governance validation. There are
no runtime or development package dependencies in this phase.

## P1–P3 dependencies

| Package | Role | Scope | Owner | Pinning status |
| --- | --- | --- | --- | --- |
| `numpy` | Numerical arrays for feature calculations | Runtime | Finahinking maintainers | `requirements.lock` |
| `pandas` | Indexed datasets and tabular transformations | Runtime | Finahinking maintainers | `requirements.lock` |
| `pytest` | Test runner | Development | Finahinking maintainers | `requirements.lock` |
| `ruff` | Static checks and formatting | Development | Finahinking maintainers | `requirements.lock` |
| `jupyterlab` | Reproducible research workspace | Research | Finahinking maintainers | `requirements.lock` |
| `ipykernel` | Notebook kernel | Research | Finahinking maintainers | `requirements.lock` |

Adding or upgrading a package requires a purpose, a compatibility note, a
review, and an update to this record and the lock file.

P4 adds no dependency; see DEPENDENCY_PROPOSAL.md.
