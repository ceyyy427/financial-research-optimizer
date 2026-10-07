from __future__ import annotations

import pytest

from finahinking.research.paper_trader import PaperLedger, PaperTrader
from finahinking.research.portfolio_runtime import PortfolioManager
from finahinking.research.risk_runtime import RiskManager


def snapshot() -> dict[str, object]:
    return {
        "snapshot_id": "snap-1",
        "as_of": "2026-10-01",
        "pit_status": "AVAILABLE",
        "observations": (
            {"instrument": "AAA", "close": 100.0, "volume": 1000.0, "available_at": "2026-10-01"},
            {"instrument": "BBB", "close": 50.0, "volume": 1000.0, "available_at": "2026-10-01"},
        ),
    }


def proposal() -> object:
    risk = RiskManager().review(snapshot(), {"status": "ADMITTED", "metrics": {"factor_score": 0.5}}, {"max_drawdown": 0.2, "max_concentration": 0.8, "min_liquidity": 100.0, "stress_scenarios": {"shock": {"drawdown": 0.1}}})
    return PortfolioManager().construct(risk, ("AAA", "BBB"), {"max_single_weight": 0.6})


def test_paper_trader_simulates_costs_slippage_and_append_only_ledger() -> None:
    ledger = PaperTrader().simulate(proposal(), snapshot(), {"fee_bps": 10, "slippage_bps": 20, "initial_cash": 10000})
    assert isinstance(ledger, PaperLedger)
    assert ledger.paper_only is True
    assert ledger.entries
    assert ledger.total_fees > 0
    assert ledger.total_slippage > 0
    copied = ledger.append({"event": "observation"})
    assert len(copied.entries) == len(ledger.entries) + 1
    assert len(ledger.entries) < len(copied.entries)


def test_paper_trader_rejects_live_execution_surface() -> None:
    with pytest.raises(ValueError, match="paper|broker|order|live|account"):
        PaperTrader().simulate(proposal(), snapshot(), {"broker": object()})

