"""P1 research environment acceptance tests.

These checks intentionally inspect the project contract rather than importing
future P2/P3 modules.  They keep the bootstrap environment small and make the
notebook workflow verifiable without network access.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _project_metadata() -> dict[str, object]:
    """Read the PEP 621 project table without adding a runtime dependency."""

    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
        pytest.fail("Python 3.11+ is required for the project metadata parser")

    pyproject = ROOT / "pyproject.toml"
    assert pyproject.exists(), "pyproject.toml must define the research environment"
    with pyproject.open("rb") as handle:
        return tomllib.load(handle)["project"]


def test_project_declares_supported_python_and_runtime_dependencies() -> None:
    metadata = _project_metadata()

    assert metadata["name"] == "finathink"
    assert str(metadata["requires-python"]).startswith(">=3.11")
    dependencies = {str(item).lower() for item in metadata["dependencies"]}
    assert any(item.startswith("numpy") for item in dependencies)
    assert any(item.startswith("pandas") for item in dependencies)


def test_package_import_exposes_version_and_keeps_p1_boundary() -> None:
    import finahinking

    assert finahinking.__version__
    assert not hasattr(finahinking, "ResearchRun")


def test_lockfile_contains_declared_runtime_and_tooling_packages() -> None:
    lockfile = ROOT / "requirements.lock"
    assert lockfile.exists()
    contents = lockfile.read_text(encoding="utf-8").lower()

    for package in ("numpy", "pandas", "pytest", "ruff", "jupyterlab", "ipykernel", "setuptools"):
        assert f"{package}==" in contents


def test_notebook_is_local_deterministic_and_has_a_kernel() -> None:
    notebook_path = ROOT / "notebooks" / "01_research_workflow.ipynb"
    assert notebook_path.exists()
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    assert notebook["nbformat"] >= 4
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )
    assert "default_rng" in source
    assert "seed" in source.lower()
    assert "http://" not in source
    assert "https://" not in source


def test_makefile_exposes_reproducible_environment_and_gate_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "install" in makefile
    assert "test" in makefile
    assert "p1-gate" in makefile
    assert "p2-gate" in makefile
