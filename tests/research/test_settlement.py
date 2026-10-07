from __future__ import annotations

from datetime import date

import pytest

from finahinking.research.paper_trader import PaperLedger, PaperLedgerEntry
from finahinking.research.settlement import SettlementEvent


def ledger(*, snapshot_digest: str = "dataset-v1") -> PaperLedger:
    return PaperLedger(
        entries=(
            PaperLedgerEntry(
                timestamp="2026-10-01",
                event="paper_fill",
                instrument="ETF:SPY",
                target_weight=0.5,
                quantity=1,
                reference_price=100,
                execution_price=100.1,
                notional=100.1,
                fees=0.01,
                slippage=0.1,
                cash=899.89,
                equity=999.99,
            ),
        ),
        snapshot_digest=snapshot_digest,
    )


def event(**overrides: object) -> SettlementEvent:
    values: dict[str, object] = {
        "run_id": "run-settlement",
        "ledger": ledger(),
        "as_of": date(2026, 10, 2),
        "realized_outcomes": {
            "factor_weights": {"value": 0.6, "quality": 0.4},
            "risk_rules": {"max_drawdown": 0.2},
            "registry": {"candidate": "factor:value:v2"},
            "net_return": 0.03,
        },
        "costs": {"fees": 0.01, "slippage": 0.1},
        "dataset_digest": "dataset-v1",
    }
    values.update(overrides)
    return SettlementEvent(**values)


def test_settlement_requires_paper_ledger_and_validates_dataset_fingerprint() -> None:
    with pytest.raises((TypeError, ValueError)):
        SettlementEvent(
            run_id="run-settlement",
            ledger=None,
            as_of="2026-10-02",
            realized_outcomes={},
            costs={},
            dataset_digest="dataset-v1",
        )
    with pytest.raises(ValueError, match="dataset"):
        event(dataset_digest="other-dataset")


def test_settlement_as_of_cannot_precede_ledger_timestamp() -> None:
    with pytest.raises(ValueError, match="as_of"):
        event(as_of="2026-09-30")


def test_settlement_fingerprint_is_stable_and_redacts_no_sensitive_payload() -> None:
    first = event()
    second = event(realized_outcomes={
        "registry": {"candidate": "factor:value:v2"},
        "net_return": 0.03,
        "risk_rules": {"max_drawdown": 0.2},
        "factor_weights": {"quality": 0.4, "value": 0.6},
    })
    assert first.fingerprint == second.fingerprint
    with pytest.raises(ValueError, match="sensitive"):
        event(realized_outcomes={"prompt": "do this"})
    with pytest.raises((ValueError, TypeError)):
        event(realized_outcomes={"raw_provider_object": object()})


@pytest.mark.parametrize(
    "field",
    (
        "provider_response",
        "providerResponse",
        "raw_provider_object",
        "rawProviderObject",
        "provider_payload",
        "rawProviderOutput",
    ),
)
def test_settlement_rejects_nested_provider_and_raw_payload_keys(field: str) -> None:
    with pytest.raises(ValueError, match="sensitive"):
        event(realized_outcomes={"nested": {field: {"value": 1}}})
