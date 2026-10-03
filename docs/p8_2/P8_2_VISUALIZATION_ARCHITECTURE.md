# Finathink P8.2 Visualization Architecture

**Status:** first local research-surface slice implemented; final UI/performance
gates pending
**Date:** 2026-10-03 (Asia/Shanghai)

## Boundary and ownership

The server and Finathink contracts own all financial meaning. The browser owns
layout, navigation, highlighting, and point selection only.

```text
FixtureMarketDataSource / future QMT adapter
              │
              ▼
DatasetSnapshot + provenance + fingerprint
              │
              ▼
build_research_payload()
              │  bounded schema-v1 JSON
              ▼
GET /api/research/series ──► local static bundle
                                  │
             ┌────────────────────┼────────────────────┐
             ▼                    ▼                    ▼
      Lightweight Charts       ECharts             HTML table
      candles/volume/          sweep panel          keyboard fallback
      crosshair/markers
             └────────────────────┬────────────────────┘
                                  ▼
                    finathink:point-selected(pointId)
                                  │
                                  ▼
                    server-owned inspector/provenance
```

No provider-specific object, calculation engine, or credential enters the
browser boundary. A `ResearchPoint` contains the values and feature/event
metadata needed for display; the controller does not derive returns, signals,
features, scores, positions, or ML metrics.

## Implemented first slice

The current implementation is in `src/finahinking/p8_2/research_view.py`,
`src/finahinking/local_app.py`, and `frontend/src/research.js`.

| Surface | Current behavior | Evidence |
| --- | --- | --- |
| Normalized payload | Schema version 1; deterministic fixture snapshot; dataset ID/fingerprint/mode/as-of/PIT flag/limitations; 12 default points | `build_research_payload()` and `FixtureMarketDataSource(points=12)` |
| Price chart | Candlestick OHLC and volume histogram; local Lightweight Charts renderer | `frontend/src/research.js` |
| Navigation | Crosshair, click selection, chart auto-size, native chart range/pan controls | Lightweight Charts controller |
| Events | Event-derived above-bar markers | `fixture-start` marker mapping |
| Research panel | ECharts line panel for six declared sweep experiments and OOS score | `renderSweep()` |
| Point inspector | Formatted timestamp/OHLCV/features/events, live region | `selectAndAnnounce()` |
| Table fallback | Text cells, `role=button`, `tabIndex=0`, Enter/Space selection, `aria-current` | `pointTable()` |
| Routes | `/research`, `/ml`, `/parameter`, `/settings/engines`, `/settings/data-sources`; JSON API routes under `/api/research/*` | local app route table |
| Asset boundary | Allow-listed `/assets/finathink-research.js`, package-data copy, no arbitrary path | `LocalApplication.asset_bytes()` |

The payload's fixture features are explicitly descriptive: one-period return,
intraday range, and chronological close rank. The server computes these before
serialization; the browser receives values and labels.

The renderer map is intentionally question-led: candles/line for price path,
volume for activity, markers for dated events/signals, line/heatmap/small
multiples for parameter sensitivity, and table/inspector for exact values and
provenance. Prediction-vs-target, residual, feature-importance, drift, and
time-split views belong to an admitted ML result; the current fallback does
not invent those series.

## Payload contract

The route returns a bounded document with:

- `schema_version`, `view`, and a payload fingerprint;
- `dataset` identity, mode, source/provider, as-of timestamp, PIT result, and
  limitations;
- ordered `points` with canonical ID, timestamp, OHLCV, features, events,
  signal label, source, provider, and availability timestamp;
- feature definitions and event descriptions;
- every parameter-sweep experiment, OOS comparison, warnings, and multiple-
  testing metadata;
- explicit limitations and sample/offline copy.

The controller rejects a missing schema/fingerprint, missing point identity,
invalid timestamps, non-finite OHLCV, an oversized point list (>10,000), and
out-of-order points. It copies feature/event arrays before rendering so the
view cannot mutate the source payload. The server remains responsible for
duplicate-point and contract-level validation.

## Renderer and asset choices

The isolated frontend workspace pins:

| Package | Version | License | Use |
| --- | --- | --- | --- |
| `lightweight-charts` | 5.2.1 | Apache-2.0 | Time-series/candlestick, volume, crosshair, markers |
| `echarts` | 6.1.0 | Apache-2.0 | Parameter/OOS comparison panel |
| `esbuild` | 0.28.2 | MIT | Reproducible IIFE bundle |

The production bundle is emitted to `site/assets/finathink-research.js` and a
package-data copy is required at
`src/finahinking/_package_data/assets/finathink-research.js`. It is served
same-origin; no CDN, remote font, or inline third-party script is required.

## Interaction and accessibility rules

- Every chart fact has a table/inspector alternative; no essential meaning is
  conveyed by hover or color alone.
- Point rows are keyboard selectable and announce a concise text summary in a
  live region. Focus-visible outlines inherit the existing shell token.
- `prefers-reduced-motion` disables chart animation and existing shell motion.
- Chart labels identify the data mode and limitations. A sample chart cannot
  look like a live feed solely because it is green or recent.
- The route keeps a readable server-rendered shell if JavaScript fails; the
  table fallback should remain the next recovery path.
- Data is displayed with tabular numerals and source/fingerprint context near
  the relevant chart or table.

## Security and failure behavior

The local shell sets a same-origin CSP (`script-src 'self'`) only because the
research bundle is now required; the asset route is allow-listed and the
server does not accept arbitrary asset names. Payload errors show an alert
region and do not create a partial research artifact. API failures remain
structured JSON errors. The browser never receives QMT tokens or optional
engine objects.

When the bundle or optional renderer is absent, the server still exposes route
copy, provenance, and a table/empty/error state. Qlib, vectorbt, and QMT are
represented as capability states, not as chart dependencies.

## Current evidence and open gates

Observed local evidence on 2026-10-03:

- `npm test`: 3 Node tests passed.
- `npm run build`: completed and emitted the bundle; the package-data copy must
  be synchronized after the final build.
- P8.2 Python focused tests: 19 passed at final review.
- No real browser/CUA session was used or claimed. Browser-level performance,
  screen-reader, and cross-browser evidence remain unverified.

Open gates are bundle-copy/package-data verification, a browser/headless DOM
smoke if available without Computer Use, 1k/10k interaction measurements,
asset/license audit, and final CSP/security review.
