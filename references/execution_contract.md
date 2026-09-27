# Backtest execution contract

Before any backtest, declare `signal_time`, `decision_time`, `execution_time`, `execution_price`, `market_calendar`, `latency_bars`, `slippage_bps`, and `partial_fill_rule`. Also document cash interest and dividend/adjustment handling when relevant.

The validator rejects same-session execution after a close signal, missing latency, and a positive slippage budget without an execution-price convention. It does not infer a favorable fill. Execution costs are applied once, on the declared fill, and must be preserved in the rolling ledger.

```bash
python3 - <<'PY'
from scripts.execution_contract import validate_execution_contract
print(validate_execution_contract({
    "signal_time": "close", "decision_time": "after_close",
    "execution_time": "next_open", "execution_price": "next_open_plus_slippage",
    "market_calendar": "XNYS", "latency_bars": 1,
    "slippage_bps": 10, "partial_fill_rule": "pro_rata"
}))
PY
```
