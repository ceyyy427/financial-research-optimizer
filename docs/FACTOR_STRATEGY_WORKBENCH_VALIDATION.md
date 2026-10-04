# Factor Strategy Workbench Validation

Validation records what is implemented in this checkout and keeps deferred or
unverified capabilities separate from passing checks.

## Required boundaries

- [x] Offline deterministic sample data is the default path.
- [x] Factor, signal, position, risk, execution, and explanation are separate
      server-owned layers.
- [x] Long-only position policy and first-version no-leverage limits are
      enforced.
- [x] Same-period fills are rejected; delayed holdings drive net returns.
- [x] FREEZE preserves existing holdings; only explicit FLATTEN exits them.
- [x] Test/OOS data stays hidden until an explicit freeze and can be evaluated
      once per frozen version.
- [x] Failed and superseded research attempts remain in immutable history.
- [x] API keys, credentials, model code, shell/SQL commands, absolute paths,
      broker operations, and external URLs are rejected from contracts.
- [x] `/workbench` and `/api/research/workbench` are read-only.
- [x] Offline HTML report output contains no external network dependency.

## Evidence to run before release

From the repository root:

```bash
python3 -m ruff check src tests
python3 -m compileall -q src tests
python3 -m pytest -q
cd frontend && npm test && npm run build
cd .. && git diff --check
```

The release record should attach the command output or CI links. A passing
static or fixture test does not prove live-provider, broker, or production
market-data readiness.

## This checkout's final verification

On 2026-10-05, the final local gate reported:

```text
python3 -m ruff check src tests  → All checks passed
python3 -m compileall -q src tests → passed
python3 -m pytest -q              → 409 passed, 1 skipped
npm test                          → 10 passed
npm run build                     → passed
git diff --check                  → passed
```

The generated browser bundle and the packaged browser asset were also byte
identical after the build.

## Completed in this phase

The implementation includes immutable policy contracts, a deterministic paper
replay engine, an allow-listed factor graph, bounded research history and
freeze/test gates, evidence-bound explanation packages, normalized workbench
payloads, the offline HTML report, the Research Workspace linkage, and a
standalone workbench launch surface.

## Deferred or unverified

Live data freshness, provider credentials, hosted-model selection, user-owned
API keys, QMT/Qlib/vectorbt production compatibility, broker permissions,
account state, order routing, real market impact, and unattended scheduling
are intentionally not tested or claimed. The workbench is a research and
education artifact, not financial advice and not a live trading system.
