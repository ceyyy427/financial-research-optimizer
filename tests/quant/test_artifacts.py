from datetime import UTC, datetime

import pytest

from finahinking.quant.artifacts import Artifact, QuantRun


def test_artifact_and_quant_run_round_trip_with_content_fingerprints():
    artifact = Artifact.create(
        artifact_id="fixture-result",
        artifact_type="backtest_result",
        payload={"equity": [100.0, 101.0], "metrics": {"sharpe": None}},
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
    )
    run = QuantRun.create(
        quant_run_id="quant-fixture",
        research_run_id="research-fixture",
        dataset_version="fixture-v1",
        strategy_version="fixture-strategy-v1",
        engine_version="p5.inhouse.0.1",
        parameters={"fee_bps": 5.0, "slippage_bps": 2.0},
        result_artifact=artifact,
        timestamp=datetime(2024, 1, 3, tzinfo=UTC),
    )
    restored = QuantRun.from_json(run.to_json())
    assert restored == run
    assert restored.fingerprint == run.fingerprint
    assert restored.result_artifact.fingerprint == artifact.fingerprint


def test_artifacts_reject_unsafe_ids_and_executable_payload_keys():
    with pytest.raises(ValueError, match="identifier"):
        Artifact.create("../escape", "result", {"value": 1})
    with pytest.raises(ValueError, match="executable"):
        Artifact.create("unsafe", "result", {"__code__": "print('no')"})
