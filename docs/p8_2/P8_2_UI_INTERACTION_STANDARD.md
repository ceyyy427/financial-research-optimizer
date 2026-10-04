# Finathink P8.2 UI Interaction Standard

**Status:** local research surfaces implemented; accessibility/browser review
continues
**Date:** 2026-10-03 (Asia/Shanghai)

## Product surfaces

| Route | Purpose | Required state disclosure |
| --- | --- | --- |
| `/research` | Candles/volume, features/events, selected-point inspector, sweep preview, table | `SAMPLE`, `PIT-AWARE`, `READ-ONLY`, fixture limitations |
| `/ml` | Typed ML specification and normalized fallback result | Qlib `NOT INSTALLED`/fallback; model/data scopes; no raw objects |
| `/parameter` | Every declared parameter experiment and OOS context | Multiple-testing warning; no winner label |
| `/settings/engines` | Core/optional engine capability cards | `AVAILABLE`, `NOT INSTALLED`, `NOT CONNECTED`, environment/version |
| `/settings/data-sources` | Fixture provenance and QMT data-health boundary | Mode, fingerprint, as-of/PIT, QMT read-only state |

Supporting JSON routes are `/api/research/series`, `/api/research/ml`,
`/api/research/parameters`, `/api/research/capabilities`, and
`/api/research/qmt`. They return Finathink-owned records only.

## Interaction vocabulary

Use explicit state text: `LIVE`, `CAPTURED`, `SAMPLE`, `SYNTHETIC`, `PAPER`,
`AVAILABLE`, `NOT INSTALLED`, `LOGIN REQUIRED`, `NOT CONNECTED`, `STALE`,
`ERROR`, `PENDING`, `RUNNING`, `COMPLETE`, and `FAILED`. Never encode one of
these states with color alone, and never imply a live source from a polished
card or recent-looking timestamp.

## Chart-to-inspector synchronization

1. Hover/crosshair may preview a canonical point, but click or keyboard table
   selection makes it persistent.
2. Selection emits only `finathink:point-selected` with `{ pointId }`.
3. The inspector resolves the point from the normalized payload and displays
   timestamp, OHLCV, features, events, signal label, source/provider, and
   limitations.
4. A selected timestamp should synchronize chart highlight, feature values,
   event context, and any valid strategy/paper metadata. It must not trigger a
   client-side financial calculation.
5. Empty, invalid, stale, or unavailable data gets a structured message and a
   recovery action; no partial result is presented as complete.

## Accessibility baseline

- Use semantic headings, landmarks, table headers/captions, labels, and live
  regions. Keep a visible skip link and visible `:focus-visible` outline.
- Interactive controls and row targets have at least a 44px effective target;
  keyboard activation supports Enter and Space.
- Every chart has a textual title, source/mode context, and accessible table or
  inspector alternative. Tooltips are supplemental, never the sole channel.
- Use text + icon/shape + color for event/signal distinctions and preserve
  sufficient contrast for muted evidence text.
- Respect `prefers-reduced-motion`; do not auto-animate research results in a
  way that changes interpretation.
- Preserve zoom/pan and table readability at narrow widths; avoid horizontal
  clipping of the source/fingerprint context.

## Table and progressive-disclosure behavior

The first table is intentionally native HTML. It supports row selection and
inspector synchronization without a virtualized dependency. Larger history
tables may add sorting, filtering, column visibility, sticky headers,
pagination, virtualization, and row inspectors only when each behavior keeps
keyboard focus and provenance visible.

Details/summary panels expose normalized ML results and limitations on demand;
the default view remains calm and readable. Low-level provider logs, tokens,
and machine paths are not shown by default.

## ML and parameter-lab minimum disclosures

An admitted ML run must show dataset/fingerprint, feature set, train window,
validation window, test/OOS window, model family/version, hyperparameters,
training/validation/OOS metrics, feature importance, prediction distribution,
error analysis, and limitations. The current offline ML surface shows the
Finathink specification, deterministic baseline metrics, fallback status, and
normalized result; richer residual/drift/prediction panels remain gated on a
real admitted model result.

The Parameter Lab may grow from the current experiment table + OOS line into
heatmaps, sensitivity curves, small multiples, and parameter tables. Every
visual must retain experiment count, declared ranges, in-sample versus OOS
context, multiple-testing warning, robust/unstable regions, and selection
policy. A heatmap cell is never labeled `BEST STRATEGY`.

## Responsive and error states

The existing shell uses a three-column desktop layout and collapses to a
single-column mobile layout. Research panels collapse into one column below
880px. The chart has a bounded responsive height; the table can scroll
horizontally without changing the source values.

The route remains meaningful when JavaScript, an optional renderer, or a
provider is unavailable: server copy, mode/fingerprint, a server-rendered
observation table, and an actionable empty/error state remain. The local
bundle enhances that table with selection synchronization; it is not the sole
content path.
`NOT INSTALLED` and `NOT CONNECTED` are capabilities, not fatal route errors.

## Research-integrity copy rules

- Say “declared experiments,” “descriptive,” “sample,” “OOS comparison,” and
  “limitations” where appropriate.
- Do not say “best strategy,” “guaranteed,” “predicts the market,” or imply a
  broker connection from a QMT capability card.
- Keep costs, slippage, benchmark, split, source, and method adjacent to a
  result or reachable in one disclosure step.
- Keep math/code/finance explanations linked to the same artifact fingerprint;
  explanatory copy cannot silently change the underlying result.

## Current evidence and pending review

The local route tests cover all five surfaces, same-origin script policy,
asset loading, explicit QMT denial list, and fixture provenance. The frontend
unit suite covers payload validation, point selection, and inspector summary.
No Computer Use or real browser session was used. Screen-reader, multi-browser,
touch, and long-history virtualization evidence remain pending and must be
recorded separately from the local parser/headless gates.
