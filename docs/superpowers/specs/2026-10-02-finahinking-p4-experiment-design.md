# Finahinking P4 Experiment Engine Design

## Objective

Add a reproducible experiment layer without changing the P0–P3 provider,
feature, or factor boundaries. A research run records what was asked, what was
hypothesized, which dataset and factor were used, how the computation was
performed, what result was obtained, and what was learned.

## Architecture

`ExperimentEngine` consumes a validated P2 `Dataset` and a P3
`FactorDefinition`. It computes a deterministic forward-return target, applies
the factor's documented callable, evaluates the factor, and creates an
immutable `ResearchRun` record. `RunStore` serializes the record as canonical
JSON. Dataset and result fingerprints make accidental input/result drift
detectable. Reproduction re-executes the same definition against the same
dataset and compares the result fingerprint.

## ResearchRun contract

Required fields: run id, question, hypothesis, dataset provenance and
fingerprint, factor name, method, parameters, result metrics, conclusion,
insight, limitations, creation timestamp, and engine version. Records are
JSON-compatible and round-trip through `to_dict`/`from_dict`.

## Execution semantics

- The first supported method is `information_coefficient`.
- A forward-return target uses `close.pct_change(horizon).shift(-horizon)`.
- Factor evaluation uses the P3 safe default of one-period factor shifting.
- Inputs must contain a validated positive `close` series and a positive
  integer horizon.
- Results are descriptive research evidence, never advice or trade signals.

## Persistence and reproducibility

`RunStore(root).save(run)` writes `<run_id>.json` atomically through a temporary
file and rejects overwrite of a different record. `load(run_id)` validates the
record schema. `ExperimentEngine.reproduce(run, dataset, factor)` recomputes
the run and raises `ReproducibilityError` if the definition, data fingerprint,
or result changes.

## Security and scope

Storage is local-only and never executes code from JSON. No credentials,
network calls, model loading, portfolio execution, or P5 behavior is included.
No new third-party dependency is needed.

## Acceptance criteria

1. A complete experiment can be created and executed from a validated dataset
   and factor.
2. A run can be saved, loaded, and reproduced with identical fingerprints.
3. Dataset mutation or changed parameters is detected as non-reproducible.
4. Malformed records and unsafe horizons fail closed.
5. Full tests, lint, governance validation, and an independent P4 gate review
   pass before stopping.
