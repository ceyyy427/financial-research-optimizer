# Known limitations

Finathink (Financial Research Optimizer) is a public beta and intentionally conservative.

- Source install is the validated distribution. A signed macOS Apple Silicon
  binary and platform installers are not claimed until a maintainer publishes
  them; there is no fabricated release asset.
- Coverage is a reviewed teaching curriculum, not a complete finance
  textbook. Source coverage and fixture dates are limited.
- Provider data may be revised, delayed, unavailable, or subject to terms and
  rate limits. Point-in-time completeness and survivorship-free universes are
  not guaranteed by sample fixtures.
- Backtests and paper simulation are research aids only. They do not model all
  fees, liquidity, market impact, corporate actions, or execution risk.
- Strategy results are not forecasts, recommendations, or guarantees. No
  broker integration, live order path, or real-money execution exists.
- AI assistance, where configured by a user, is not an authoritative source;
  all claims and knowledge contributions require evidence and review.
- Local backups, filesystem permissions, and user-selected provider terms are
  outside the application's control.
- The community projection model is evidence-linked and non-hype; it is not a
  social ranking, moderation service, or financial advice channel.
- The final Task 17 gate has two known isolated failures: the autonomous
  concurrent worker runs can hit a fork plus `multiprocessing.Queue`
  feeder-thread race that is surfaced as `RESOURCE_LIMIT`; this remains
  deferred until the worker architecture is made fork-safe and rerun.
- The offline vertical-slice fixture now uses an explicit resolver injection
  seam (`f5d1a61`); the default resolver remains fail-closed for unverified
  targets.
- Ruff is clean for the current source, test, and script tree (`python3 -m ruff
  check src tests scripts`); this does not change the two independent runtime
  failures above or the conditional release status.
- A bounded local Playwright/Chromium acceptance exists (`OFFLINE_BROWSER_PASS`:
  4 tests, 7 HTML/PNG artifacts, hash verified). Portable reruns may skip browser
  cases when the browser binary is absent. Real external provider, vendor,
  browser/device, and production deployment behavior remains externally
  unverified in this checkout.
