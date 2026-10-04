# Factor Strategy Workbench

The Factor Strategy Workbench is Finathink's offline, paper-only surface for
turning a factor idea into an inspectable strategy replay. It is designed for
research and learning, not for live trading or investment advice.

## What is implemented

The current path has six explicit layers:

1. **Data** — a deterministic, point-in-time-aware fixture snapshot with a
   dataset fingerprint and source availability fields.
2. **Factor** — an allow-listed factor graph with bounded primitives such as
   `return`, `rolling`, `lag`, `normalize`, `rank`, `winsorize`, `combine`, and
   `filter`.
3. **Signal** — a score or eligibility observation kept separate from capital
   allocation.
4. **Position and risk** — long-only policy mappings, caps, cash buffer,
   turnover/liquidity limits, risk states, hysteresis, and allow-listed risk
   actions.
5. **Execution** — delayed paper holdings with deterministic fees, slippage,
   blocked trades, and fault events. Same-period fills are rejected.
6. **Explanation** — a paired baseline/variant package covering concept,
   intuition, math, derivation, code trace, finance meaning, parameter effect,
   result fields, assumptions, limitations, and the next experiment.

The same server-owned payload feeds the Research Workspace, the standalone
`/workbench` page, and the offline HTML report. The browser selects and
explains values; it does not recalculate financial metrics or write a strategy.

## Research workflow

Use the bounded loop below when extending a factor:

```text
question → charter → factor graph → train/validation attempts
→ keep/reject history → explicit freeze → one test evaluation
→ explanation package → paper report
```

`ResearchCharter` fixes the question, data split, evaluation metrics, hard
constraints, allowed primitives, and experiment budget. `ResearchSession`
retains every attempt. There is no `BEST` status: a kept candidate must be
explicitly frozen before test/OOS metrics can be read, and a frozen version can
be evaluated only once. `WorkbenchStore` saves, reopens, lists history, and
rolls back to immutable content-addressed versions.

## Local use

Install the development dependencies and start the sample application:

```bash
python3 -m pip install -e '.[dev]'
python3 scripts/run_local_app.py --sample --port 8765
```

Open [http://127.0.0.1:8765/workbench](http://127.0.0.1:8765/workbench). The
page is read-only and works without a market-data account. The Research page
links to it, and the page keeps a keyboard-accessible table beside the
interactive selection layer.

The read-only JSON entry point is:

```text
GET /api/research/workbench
```

The payload includes the run ID, policy and dataset fingerprints, metrics,
factor observations, signals, raw and final weights, delayed holdings, cash,
risk states, trades, costs, slippage, fault events, report references, and
limitations. `POST` is intentionally rejected.

## Offline HTML reports

`ReportBundleWriter` writes `workbench/index.html` beside the main report.
The document is self-contained: CSS and SVG are inline, there are no CDN
requests, no external fonts, no JavaScript dependency, and the paper-only
boundary is visible in the title, status, evidence chain, table, and footer.
It can be copied or archived as a research artifact without a running server.

## Explicitly deferred

This phase does **not** connect a live market feed, ask users for API keys,
call a hosted model, download a user's provider, connect a broker, submit or
cancel orders, manage an account, or run an unattended daemon. Those are
future adapter and product decisions after there is a user and a reviewed
credential boundary. No API key, token, password, secret, private key, URL,
absolute local path, callable, model code, SQL, shell command, or broker
operation is accepted into the policy contracts or report payloads.

## Reading a result

Read the chain in order. A high factor score is only an observation. The
position policy may cap or normalize it; risk state may scale or hold it; the
execution policy may delay it; costs and slippage may reduce the net result.
When a fault occurs, inspect the allow-listed action and the resulting held
weight. Never interpret a fixture replay as a forecast or a trading instruction.
