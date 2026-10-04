import pandas as pd

from finahinking.p6.gateway import P6QuantGateway
from finahinking.p6_5.models import Event
from finahinking.p6_5.quant_bridge import EventQuantBridge


def test_event_quant_bridge_reuses_typed_p6_gateway() -> None:
    event = Event(
        event_id="event-1",
        event_type="MACRO_RELEASE",
        source_id="bls",
        reference_period="2024-12",
        published_at="2025-01-15T08:30:00-05:00",
        available_at="2025-01-15T13:31:00Z",
        observation_ids=("obs-1",),
        evidence_ids=("evidence-1",),
    )
    bridge = EventQuantBridge(P6QuantGateway())
    response = bridge.run(event, "user-1", frame=pd.DataFrame(
        [
            {"date": "2020-01-01", "asset": "AAA", "close": 100, "available_at": "2020-01-01"},
            {"date": "2020-01-01", "asset": "BBB", "close": 100, "available_at": "2020-01-01"},
            {"date": "2020-01-02", "asset": "AAA", "close": 110, "available_at": "2020-01-02"},
            {"date": "2020-01-02", "asset": "BBB", "close": 95, "available_at": "2020-01-02"},
            {"date": "2020-01-03", "asset": "AAA", "close": 121, "available_at": "2020-01-03"},
            {"date": "2020-01-03", "asset": "BBB", "close": 90, "available_at": "2020-01-03"},
            {"date": "2020-01-04", "asset": "AAA", "close": 120, "available_at": "2020-01-04"},
            {"date": "2020-01-04", "asset": "BBB", "close": 92, "available_at": "2020-01-04"},
            {"date": "2020-01-05", "asset": "AAA", "close": 130, "available_at": "2020-01-05"},
            {"date": "2020-01-05", "asset": "BBB", "close": 88, "available_at": "2020-01-05"},
        ]
    ))
    assert response.status == "SUCCEEDED"
    assert response.quant_run_id
    assert response.provenance["gateway"] == "finahinking-p6-v1"
    assert response.provenance["request_context"]["event_id"] == event.event_id
