import json

import pytest

from finahinking.experiments.engine import ExperimentEngine
from finahinking.experiments.storage import RunStore
from finahinking.factors.core import momentum_factor

from .test_engine import dataset


def test_run_store_saves_and_loads_research_run(tmp_path):
    run = ExperimentEngine().execute("q", "h", dataset(), momentum_factor(2), 1, "c", "i", run_id="run-1")
    store = RunStore(tmp_path)
    path = store.save(run)
    assert path.name == "run-1.json"
    assert store.load("run-1") == run


def test_run_store_rejects_path_traversal_and_malformed_json(tmp_path):
    store = RunStore(tmp_path)
    with pytest.raises(ValueError, match="run id"):
        store.load("../escape")
    (tmp_path / "bad.json").write_text(json.dumps({"run_id": "bad"}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        store.load("bad")
