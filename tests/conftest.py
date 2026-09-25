from pathlib import Path
import pytest


ROOT_PATH = Path(__file__).resolve().parents[1]
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
