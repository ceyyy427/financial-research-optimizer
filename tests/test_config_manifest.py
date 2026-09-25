import json

import pytest

from config_utils import load_config, validate_config
from manifest_utils import load_manifest


def test_research_config_is_valid(CONFIG):
    config = load_config(CONFIG)
    assert config["universe"] == ["SPY", "TLT", "GLD"]
    assert config["evaluation"]["method"] == "expanding_window"
    assert len(config["_config_fingerprint"]) == 16


def test_invalid_config_is_rejected():
    errors = validate_config({"universe": []})
    assert any("missing top-level" in error for error in errors)


def test_experiment_manifest_is_valid(MANIFEST):
    manifest = load_manifest(MANIFEST)
    assert manifest["experiment_id"].startswith("spy-tlt-gld")
    assert manifest["reproducibility_status"] == "complete"
