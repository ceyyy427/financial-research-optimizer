# Finathink P8.2 Research Engine Architecture

**Status:** architecture contract for the local P8.2 slice
**Date:** 2026-10-03 (Asia/Shanghai)

## Design principle

External engines may accelerate a bounded research operation, but they are
providers, not Finathink's domain. The authoritative path is:

```text
source / fixture / QMT bridge
  → MarketObservation / DatasetSnapshot
  → FeatureDefinition / FeatureObservation
  → StrategySpec / MLResearchSpecification
  → ResearchRun / QuantRun / ParameterSweep
  → Artifact + provenance + fingerprint
  → normalized JSON view model
  → chart, table, inspector, learning trace
```

This keeps the educational chain visible: question → data → feature → target
→ split → model/strategy → train/backtest → validation → OOS → explanation →
learning. A chart or third-party result cannot bypass a validity boundary.

## Finathink-owned contracts

P8.2 contracts are immutable, JSON-safe, bounded, and fingerprintable. The
planned records are:

| Record | Required meaning | Integrity rules |
| --- | --- | --- |
| `MarketObservation` | One instrument/time observation and source mode | Finite OHLCV, timezone-aware timestamp, symbol/venue identifiers |
| `DatasetSnapshot` | Ordered observations plus source/provenance | No duplicate/out-of-order rows; source and snapshot fingerprint |
| `FeatureObservation` | Feature value at an as-of timestamp | PIT availability, feature definition/version, lineage |
| `ResearchPoint` | Chart/inspector row joining market, features, events, signal metadata | Canonical point ID; bounded events/features; no executable payload |
| `ParameterSweepSpecification` | Explicit parameter grid, split, costs, selection policy | Bounded cell count; train/validation/OOS periods; no implicit winner |
| `SweepResult` | All cells, metrics, warnings, robust/unstable regions | Deterministic order; multiple-testing disclosure; OOS labels |
| `MLResearchSpecification` / result | Model family, features, splits, resource limits, metrics | Allow-listed model identity; artifact and environment fingerprints |
| `ResearchRun` / `QuantRun` | Durable research lineage and outcome | Existing Finathink fingerprints, provenance, limitations, no broker fields |

Every contract rejects non-finite numbers, invalid identifiers, duplicate
timestamps, unbounded collections, and fields that could smuggle credentials or
executable code. Canonical JSON is the digest input; display formatting never
changes the fingerprint.

## Engine layers

### 1. Internal Finathink engine (authoritative fallback)

The existing quant/research modules provide deterministic fixtures, factor and
regression analysis, strategy/paper research, cost/slippage assumptions, and
artifact storage. P8.2 adds contracts and view models without replacing the
existing P5/P6.5/P6.6 validity machinery.

The internal parameter sweep enumerates a bounded grid in deterministic order,
evaluates each cell through a Finathink-owned evaluator, and reports:

- experiment count and failed/pending cells;
- train/validation/OOS windows and dataset fingerprints;
- metric definitions, costs, slippage, benchmark, and assumptions;
- multiple-testing and selection warnings;
- robust and unstable regions;
- limitations and reproducibility information.

It may expose a “reference cell” for inspection, but must not label one cell
`BEST STRATEGY` or turn a sample result into advice.

### 2. Qlib adapter (optional C sandbox)

`QlibResearchAdapter` is a typed boundary around a future, isolated Qlib
environment. It accepts only Finathink-owned dataset/feature fingerprints,
explicit train/validation/OOS periods, model family/configuration, resource
limits, and provenance. It returns a Finathink ML result containing model and
environment identity, split fingerprints, metrics, prediction artifact,
warnings, and limitations.

Raw Qlib handlers, datasets, models, workflow objects, and result classes are
never serialized into `ResearchRun`, passed to the browser, or imported during
core startup. If Qlib is missing or incompatible, the registry reports
`NOT INSTALLED` and the internal deterministic baseline remains available.

The audited local runtime has Python 3.13.7 and no Python 3.12 interpreter was
found; Qlib's published metadata currently lists classifiers through 3.12.
Therefore no Qlib training result is claimed until a dedicated Python 3.12
spike passes its own gates.

### 3. vectorbt adapter (optional C sandbox)

vectorbt may accelerate parameter grids and sensitivity maps in a dedicated
environment. The adapter translates a Finathink sweep specification to an
internal provider call and normalizes all cells back into `SweepResult`.

The adapter must preserve OOS boundaries, transaction costs, data lineage,
multiple-testing metadata, and failure cells. It cannot select a winner, expose
raw `Portfolio` objects, or make vectorbt a mandatory/public dependency. The
Apache-2.0 + Commons Clause license and optional extra licenses require a
distribution review before bundling/hosting.

### 4. ML and generated-code boundary

Model configuration is an allow-listed record, not arbitrary Python. Generated
educational code is a displayed artifact with static safety checks; user text
never becomes executable code. Model output is evidence with uncertainty and
limitations, not a forecast or an investment instruction.

## Research state machine

Long-running work exposes bounded, truthful stages:

```text
PENDING
  → PREPARING_DATA
  → FEATURE_ENGINEERING
  → TRAINING_OR_BACKTESTING
  → OOS_EVALUATION
  → ROBUSTNESS
  → EXPLANATION
  → ARTIFACT_SAVE
  → COMPLETE
```

Any stage may terminate in `FAILED` with a structured reason and recoverable
next action. A missing optional engine is `NOT INSTALLED`, not `FAILED`; no-data
and provider-unavailable conditions remain distinct. The UI may subscribe to
stage summaries but does not infer completion from a spinner or partial prose.

## Validity and provenance gates

Before a result is renderable, the engine checks:

1. source mode and provenance are present;
2. observation timestamps are ordered and available as of the requested time;
3. feature/target windows do not leak future information;
4. train/validation/OOS splits are explicit and non-overlapping where
   required;
5. fees, slippage, benchmark, annualization, and liquidity assumptions are
   recorded;
6. every parameter cell and failed/pending cell is retained;
7. the artifact fingerprint includes code/config/data/environment identity.

The browser may sort/filter/highlight/select, but it cannot recompute any
domain metric. A selected point resolves to its canonical ID and then to the
server-owned feature/event/signal/provenance record.

## Failure and fallback contract

| Condition | Engine response | UI state |
| --- | --- | --- |
| Optional package absent | Typed capability result; no import at core startup | `NOT INSTALLED`; internal fallback |
| Provider cannot answer | Structured `UNAVAILABLE` with source context | Recovery action; no fabricated values |
| No valid observations | `NO_DATA_AVAILABLE` | Empty state with requested period/source |
| PIT/split violation | Reject run before persistence | Validation error; no partial artifact |
| One sweep cell fails | Retain failure in result; continue independent cells | Failure count and details |
| Invalid model/code request | Allow-list rejection | Explain safe supported choices |
| QMT disconnect/stale | Preserve last known metadata only when explicitly labeled | `DISCONNECTED`/`STALE`; never `LIVE` |

## Verification map

- Contract tests: validation, JSON round trip, fingerprints, bounds, PIT.
- Sweep tests: deterministic enumeration, all-cell retention, OOS labels,
  multiple-testing warnings, no winner language.
- Adapter tests: optional-import absence, typed normalization, raw-object
  non-leakage, environment metadata.
- Route/chart tests: normalized payload, selected-point table, CSP/asset
  allow-list, no client-side financial calculation.
- Reproducibility tests: same fixture/config → same artifact fingerprint;
  changed source/config → changed fingerprint.
- Full gates: existing pytest, Ruff, governance, notebook, pip/audit,
  clean-install, secret scan, and `git diff --check`.
