from pathlib import Path
import sys
import pytest


ROOT_PATH = Path(__file__).resolve().parents[1]
# Keep collection reproducible when the repository is tested from a fresh
# checkout before editable installation.  CI still installs ``.[test,pdf]``;
# this path bootstrap makes the documented ``python3 -m pytest -q`` command
# equally reliable for local reviewers and isolated test runners.
for _path in (ROOT_PATH, ROOT_PATH / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
FIXTURE_PATH = ROOT_PATH / "tests" / "fixtures" / "synthetic_financial.csv"
CONFIG_PATH = ROOT_PATH / "examples" / "research_config.json"
MANIFEST_PATH = ROOT_PATH / "examples" / "experiment_manifest.json"


@pytest.fixture
def ROOT():
    return ROOT_PATH


@pytest.fixture
def FIXTURE():
    return FIXTURE_PATH


@pytest.fixture
def CONFIG():
    return CONFIG_PATH


@pytest.fixture
def MANIFEST():
    return MANIFEST_PATH
