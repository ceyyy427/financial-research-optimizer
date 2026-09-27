"""Validate the market execution convention used by a backtest."""
from __future__ import annotations


REQUIRED = ("signal_time", "decision_time", "execution_time", "execution_price",
            "market_calendar", "latency_bars", "slippage_bps", "partial_fill_rule")


def validate_execution_contract(contract):
    errors = []
    contract = contract or {}
    missing = [field for field in REQUIRED if field not in contract or (contract[field] == "" and field != "latency_bars")]
    errors.extend(f"missing execution field: {field}" for field in missing)
    latency = contract.get("latency_bars")
    if not isinstance(latency, int) or latency < 0:
        errors.append("latency_bars must be a non-negative integer")
    if not isinstance(contract.get("slippage_bps"), (int, float)) or contract.get("slippage_bps", -1) < 0:
        errors.append("slippage_bps must be non-negative")
    signal = str(contract.get("signal_time", "")).lower()
    decision = str(contract.get("decision_time", "")).lower()
    execution = str(contract.get("execution_time", "")).lower()
    price = str(contract.get("execution_price", "")).lower()
    if "close" in signal and ("same" in execution or execution == signal):
        errors.append("same-session execution is invalid when the signal uses the session close")
    if "close" in signal and latency == 0 and "next" not in execution:
        errors.append("close signal requires next-bar execution or an explicit non-zero latency")
    if decision and signal and decision == signal and "close" in signal and latency == 0:
        errors.append("decision_time cannot reuse an unavailable close before the close is observed")
    if "slippage" not in price and contract.get("slippage_bps", 0) > 0:
        errors.append("execution_price must state how slippage is applied")
    return {
        "valid": not errors,
        "errors": errors,
        "invariants": {
            "no_future_close_in_signal": "close" not in signal or "same" not in signal,
            "no_same_bar_close_execution": not ("close" in signal and ("same" in execution or execution == signal)),
            "latency_declared": isinstance(latency, int) and latency >= 0,
            "slippage_declared": isinstance(contract.get("slippage_bps"), (int, float)),
            "calendar_declared": bool(contract.get("market_calendar")),
            "partial_fill_rule_declared": bool(contract.get("partial_fill_rule")),
        },
    }
