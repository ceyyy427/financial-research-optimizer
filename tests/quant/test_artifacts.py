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
    with pytest.raises((TypeError, ValueError), match="executable"):
        Artifact.create("unsafe", "result", {"__code__": "print('no')"})
    with pytest.raises(ValueError, match="non-finite"):
        Artifact.create("nan", "result", {"value": float("nan")})
    with pytest.raises((TypeError, ValueError), match="payload"):
        Artifact.from_dict(
            {
                "artifact_id": "malformed",
                "artifact_type": "result",
                "schema_version": 1,
                "payload": [],
                "created_at": "2024-01-01T00:00:00",
                "fingerprint": "ignored",
            }
        )
    for key in ("eval", "exec", "__import__", "callable", "module"):
        with pytest.raises((TypeError, ValueError), match="executable"):
            Artifact.create("unsafe-key", "result", {key: "blocked"})
    with pytest.raises(TypeError, match="executable"):
        Artifact.create("unsafe-value", "result", {"value": lambda: None})


def test_artifact_deserialization_reapplies_size_limit():
    with pytest.raises(ValueError, match="size limit"):
        Artifact.from_dict(
            {
                "artifact_id": "oversized",
                "artifact_type": "result",
                "schema_version": 1,
                "payload": {"blob": "x" * 1_000_001},
                "created_at": "2024-01-01T00:00:00",
                "fingerprint": "ignored",
            }
        )


def test_artifact_and_quant_run_defensively_copy_nested_payloads_and_parameters():
    payload = {"metrics": {"value": 1.0}}
    artifact = Artifact.create("copy-safe", "result", payload)
    payload["metrics"]["value"] = 9.0
    exposed = artifact.payload
    exposed["metrics"]["value"] = 8.0
    assert artifact.payload["metrics"]["value"] == 1.0

    parameters = {"nested": {"fee_bps": 5.0}}
    run = QuantRun.create(
        quant_run_id="copy-safe-run",
        research_run_id="research",
        dataset_version="dataset",
        strategy_version="strategy",
        engine_version="engine",
        parameters=parameters,
        result_artifact=artifact,
        timestamp="2024-01-01T00:00:00",
    )
    parameters["nested"]["fee_bps"] = 99.0
    run.parameters["nested"]["fee_bps"] = 88.0
    assert run.parameters["nested"]["fee_bps"] == 5.0

    with pytest.raises(ValueError, match="executable"):
        QuantRun.create(
            quant_run_id="unsafe-parameters",
            research_run_id="research",
            dataset_version="dataset",
            strategy_version="strategy",
            engine_version="engine",
            parameters={"exec": "blocked"},
            result_artifact=artifact,
        )
