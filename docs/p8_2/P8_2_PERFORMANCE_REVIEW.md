# Finathink P8.2 Performance Review

**Status:** preliminary local measurement; performance gate not yet final
**Date:** 2026-10-03 (Asia/Shanghai)

## Scope

The review covers normalized payload construction, frontend bundle weight,
headless validation, chart/table interaction design, and the optional sweep/ML
surfaces. It does not claim hardware-independent browser FPS or real QMT
latency. No Computer Use/browser GUI session was used.

## Observed baseline

Measurements captured during the local P8.2 slice:

| Item | Observed value | Interpretation |
| --- | ---: | --- |
| Fixture chart points | 12 | Offline product fixture, not a scale limit |
| Parameter experiments | 6 | Bounded declared sample sweep |
| Frontend package tests | 4 passed | Node unit/normalization/duplicate-identity tests |
| P8.2 Python focused tests | 19 passed | Contracts, capability/QMT, sweep/adapter, route/UI tests |
| Built JS bundle | 688,040 bytes (`site/assets/finathink-research.js`) | Includes Lightweight Charts + ECharts; optimization remains possible |
| Core point guard | 10,000 points in browser normalizer | Prevents unbounded browser payloads; not a performance guarantee |
| QMT request guard | 1–256 observations | Keeps bridge responses bounded |

An inline Node benchmark of the pure payload normalizer/linear point lookup
(Node v24.21.0, one run per size, synthetic data) observed:

| Synthetic points | JSON bytes | normalize + middle-point selection |
| ---: | ---: | ---: | ---: |
| 1,000 | 175,900 | 2.189 ms |
| 10,000 | 1,833,704 | 20.231 ms |

These are directional Node-only measurements, not browser render or memory
results. The 10,000-point payload also exceeds the current server contract's
1 MB JSON bound, so it is useful as a rejection/normalizer stress case rather
than a supported route size.

For a separate local Python smoke (100 sequential in-process calls, SQLite
`:memory:`, `.venv` Python 3.13.7), the research APIs averaged 3.119 ms and
10,312 bytes for `/api/research/series`, 2.333 ms and 3,398 bytes for
`/api/research/ml`, and 2.793 ms and 4,764 bytes for
`/api/research/parameters`. These numbers include deterministic fixture and
contract construction, not network, browser paint, or concurrent load.

The bundle is intentionally local and dependency-pinned, but its current size
is material for first load. A future split or lazy loading of the sweep panel
should be considered after measuring actual route behavior.

## Performance model

The critical path is:

```text
server fixture/adapter → JSON serialization → fetch
→ payload validation → chart series allocation
→ table row creation + inspector updates
```

The controller uses transforms/internal chart APIs rather than layout-driven
animation, creates one native table, and keeps server calculations out of
pointer handlers. Crosshair selection currently searches the normalized point
array; at 10,000 points this is acceptable for a smoke slice but should become
an indexed lookup if larger histories are admitted. Repeated mounting should
also dispose chart instances and resize listeners; lifecycle cleanup is an
open hardening item.

## Required benchmark matrix

The final gate should run the same deterministic fixture generator at 1,000
and 10,000 points and record:

1. payload construction and JSON byte size;
2. server serialization/parse time;
3. client normalization time;
4. chart series setup time and peak memory where a headless browser is
   available;
5. point-selection latency for first/middle/last points;
6. table creation time and keyboard selection latency;
7. sweep panel setup time for the declared experiment count.

Report medians and a small sample count, machine/runtime versions, and whether
the measure is Node-only or browser-observed. Do not turn a synthetic benchmark
into a claim about QMT or user hardware.

## Guardrails and mitigations

- Keep server point/sweep limits explicit and reject oversized payloads before
  rendering.
- Use one chart instance per mount, cleanup on route teardown, and avoid
  repeated global resize listeners.
- Prefer lazy loading or code splitting if the 682KB bundle harms first paint;
  preserve the no-remote-script policy.
- Retain the native table fallback, but paginate/virtualize only after a
  keyboard/provenance review for long histories.
- Keep optional Qlib/vectorbt work outside the interactive request path; long
  jobs report bounded progress and persist artifacts asynchronously.
- Do not optimize by removing source mode, fingerprints, limitations, or OOS
  context from the visible result.

## Current gate status

The local Node tests and build pass; focused Python tests pass at the stated
snapshot. A full 1k/10k benchmark, real browser paint/interaction trace,
screen-reader timing, mobile-device test, and QMT latency test are **NOT
VERIFIED**. The final validation report must attach those measurements or mark
them deferred with the exact environment blocker.
