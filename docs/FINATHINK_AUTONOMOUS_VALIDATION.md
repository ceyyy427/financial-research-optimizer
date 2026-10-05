# Finathink Autonomous Delivery Validation

**Scope:** `codex/factor-strategy-workbench` · 2026-10-05

This record separates implemented local behavior from optional or deferred
capabilities. It is the release gate for the autonomous delivery report.

## Completion matrix

| Area | State | Evidence |
| --- | --- | --- |
| Factor expression safety | Implemented and tested | `src/finahinking/factors/dsl.py`, `tests/research/test_factor_dsl.py`; AST allow-list, bounded windows, no arbitrary `eval` |
| Candidate mining | Implemented and tested | `src/finahinking/factors/mining.py`; deterministic bounded templates and fingerprints |
| Factor metrics | Implemented and tested | `src/finahinking/factors/evaluation.py`; IC/ICIR, quantiles, long-short, turnover/cost, decay, T+1 and PIT checks |
| Factor admission history | Implemented and tested | `src/finahinking/factors/registry.py`; append-only admission evidence |
| Research loop | Implemented and tested | `src/finahinking/research/factor_loop.py`; charter, budget, rejected attempts, freeze-before-test, once-only test |
| Provider/API-key boundary | Implemented and tested | `src/finahinking/research/provider_status.py`, `GET /api/research/providers`, `/settings/providers`; only credential references/status are exposed |
| Multi-role research contracts | Implemented locally | `src/finahinking/research/contracts.py`, `workflow.py`, `drivers.py`; offline driver is deterministic, Codex handoff is explicit |
| Workbench/UI/report evidence | Implemented and tested | `research_view.py`, `local_app.py`, `reports.py`, frontend contract tests; factor ledger appears in JSON/UI/offline HTML |
| Live market data | Deferred | User-owned data adapter and compliance review required |
| Hosted model/provider invocation | Deferred | User-owned adapter and credential boundary required; no SDK is installed by this delivery |
| Broker/account/order operations | Explicitly unavailable | Paper-only boundary; no broker credentials, order, cancel, account, or money movement contract |
| High-frequency/unattended daemon | Deferred | Outside current low-frequency, local research scope |
| External GitHub projects | Isolated reference-only | See `docs/GITHUB_REFERENCE_CATALOG.md` and `/Users/mac/.codex/references/finathink-github-20261005/`; no runtime dependency admitted |

## Required verification commands

Run from the repository root:

```bash
python3 -m ruff check src tests
python3 -m compileall -q src tests
python3 -m pytest -q
cd frontend && npm test && npm run build
cd ..
python3 scripts/secret_scan.py
python3 scripts/validate_governance.py .
git diff --check
```

The final report must record fresh output for every command. A zero exit code
is necessary but not sufficient: generated HTML is also inspected for
paper-only wording, escaped values, no external network assets, and no secret
text.

## Observed local run

- `python3 -m ruff check src tests` — passed.
- `python3 -m compileall -q src tests` — passed.
- `python3 -m pytest -q` — `432 passed, 1 skipped in 32.02s`.
- `cd frontend && npm test` — `11 passed`.
- `cd frontend && npm run build` — passed; packaged research asset regenerated.
- `python3 scripts/secret_scan.py` — `secret scan passed (no known credential patterns)`.
- `python3 scripts/validate_governance.py .` — `PASS: governance validation passed`.
- `git diff --check` — passed after generated-asset whitespace normalization.
- Generated offline HTML — factor ledger present, `PAPER-ONLY` present, 0
  external URL markers, 0 `api_key` markers; artifact size 17,598 bytes.

## Release gate

The branch is ready to push only when the full command set passes, the working
tree is clean, the generated offline report is readable, and GitHub CI passes.
Any optional provider, live-data, broker, or real-money claim remains outside
the completion claim even when a user later supplies an API key.
