import hashlib
import json
from pathlib import Path

import pytest

from finahinking.p6_5.bls import BLSClient, BLSCPIAdapter, BLSQuarantineError
from finahinking.p6_5.models import SourceRelease

FIXTURE = Path(__file__).parents[2] / "fixtures" / "p6_5" / "bls_cpi_2024_2025.json"


def test_replay_preserves_raw_payload_and_parses_observed_bls_shape() -> None:
    captured = BLSClient.replay(
        FIXTURE,
        capture_id="capture-bls-fixture",
        retrieved_at="2025-01-15T13:32:00Z",
        first_observed_at="2025-01-15T13:31:00Z",
    )
    assert captured.capture.payload_hash == hashlib.sha256(captured.raw_bytes).hexdigest()
    assert captured.capture.endpoint_id == "bls-cpi-v2"
    assert json.loads(captured.raw_bytes)["Results"]["series"]
    release = SourceRelease(
        release_id="bls-cpi-2024-12",
        source_id="bls",
        endpoint_id="bls-cpi-v2",
        event_type="MACRO_RELEASE",
        reference_period="2024-12",
        published_at="2025-01-15T08:30:00-05:00",
        available_at="2025-01-15T13:30:00Z",
        release_url="https://www.bls.gov/news.release/archives/cpi_01152025.htm",
    )
    parsed = BLSCPIAdapter.parse_capture(captured.capture, release_by_period={release.reference_period: release})
    assert len(parsed.observations) == 6
    assert len(parsed.quarantined) == 2
    assert parsed.input_rows == 8
    assert parsed.reconciled is True
    december = [item for item in parsed.observations if item.reference_period == "2024-12"]
    assert len(december) == 2
    assert december[0].latest.published_at == release.published_at
    assert december[0].latest.available_at == "2025-01-15T13:31:00Z"


def test_missing_value_is_quarantined_and_never_silently_discarded() -> None:
    raw = {
        "status": "REQUEST_SUCCEEDED",
        "Results": {"series": [{"seriesID": "CUUR0000SA0", "data": [{"year": "2024", "period": "M01", "value": "-", "footnotes": [{"code": "X"}]}]}]},
    }
    captured = BLSClient.capture_bytes(
        json.dumps(raw, separators=(",", ":")).encode(),
        capture_id="capture-quarantine",
        request_payload={"seriesid": ["CUUR0000SA0"], "startyear": "2024", "endyear": "2024"},
        retrieved_at="2025-01-15T13:32:00Z",
        first_observed_at="2025-01-15T13:32:00Z",
    )
    parsed = BLSCPIAdapter.parse_capture(captured.capture)
    assert not parsed.observations
    assert parsed.quarantined[0]["reason"] == "missing_or_non_numeric_value"
    assert parsed.quarantined[0]["footnotes"]


def test_schema_drift_is_a_hard_failure_not_a_compatibility_guess() -> None:
    raw = {"status": "REQUEST_SUCCEEDED", "Results": [{"series": []}]}
    captured = BLSClient.capture_bytes(
        json.dumps(raw).encode(),
        capture_id="capture-shape-drift",
        request_payload={"seriesid": ["CUUR0000SA0"], "startyear": "2024", "endyear": "2024"},
        retrieved_at="2025-01-15T13:32:00Z",
        first_observed_at="2025-01-15T13:32:00Z",
    )
    with pytest.raises(BLSQuarantineError, match="Results shape"):
        BLSCPIAdapter.parse_capture(captured.capture)


def test_source_reported_failure_is_not_parsed_as_success() -> None:
    raw = {"status": "REQUEST_FAILED", "message": ["bad request"], "Results": {"series": []}}
    captured = BLSClient.capture_bytes(
        json.dumps(raw).encode(),
        capture_id="capture-source-failure",
        request_payload={"seriesid": ["CUUR0000SA0"], "startyear": "2024", "endyear": "2024"},
        retrieved_at="2025-01-15T13:32:00Z",
        first_observed_at="2025-01-15T13:32:00Z",
    )
    with pytest.raises(BLSQuarantineError, match="status"):
        BLSCPIAdapter.parse_capture(captured.capture)


def test_unadmitted_series_is_quarantined_per_source_row() -> None:
    raw = {
        "status": "REQUEST_SUCCEEDED",
        "Results": {"series": [{"seriesID": "CUUR99999999", "data": [
            {"year": "2024", "period": "M01", "value": "1"},
            {"year": "2024", "period": "M02", "value": "2"},
        ]}]},
    }
    captured = BLSClient.capture_bytes(
        json.dumps(raw).encode(), capture_id="capture-unknown", request_payload={"seriesid": ["CUUR99999999"], "startyear": "2024", "endyear": "2024"},
        retrieved_at="2025-01-15T13:32:00Z", first_observed_at="2025-01-15T13:32:00Z",
    )
    parsed = BLSCPIAdapter.parse_capture(captured.capture)
    assert parsed.input_rows == 2
    assert len(parsed.quarantined) == 2


def test_client_rejects_unbounded_or_unallowlisted_requests() -> None:
    with pytest.raises(ValueError, match="series"):
        BLSClient().validate_request(["bad"], 2024, 2024)
    with pytest.raises(ValueError, match="20 years"):
        BLSClient().validate_request(["CUUR0000SA0"], 2000, 2021)
    with pytest.raises(ValueError, match="allowlisted"):
        BLSClient(endpoint="https://example.com").validate_request(["CUUR0000SA0"], 2024, 2024)
