# P4 Gate Design — Experiment Engine

## Objective

Create a reproducible `ResearchRun` that records question, hypothesis, dataset,
factor, method, parameters, result, conclusion, and insight, then save and
reproduce it locally.

## Success criteria

- A validated dataset and factor produce a complete ResearchRun.
- The run round-trips through local JSON storage.
- Reproduction returns an identical result fingerprint.
- Dataset or parameter drift is detected and reported.

## Architecture requirements

- Reuse P2 Dataset/Provenance and P3 FactorDefinition contracts.
- Keep execution, record modeling, and storage in separate modules.
- Use canonical JSON and SHA-256 fingerprints; no pickle or code execution.

## Security requirements

- Local-only storage with path-safe run IDs and atomic writes.
- Reject malformed records, invalid horizons, missing close prices, and unsafe paths.
- Do not store secrets or transmit user data.

## Testing requirements

- Unit tests cover normal execution, round-trip, drift, malformed JSON, NaN metrics,
  and invalid inputs.
- Full suite, Ruff, governance validation, and pip checks pass offline.

## Documentation requirements

- Document the method, assumptions, limitations, and P5 boundary.
- Record the no-new-dependency decision in proposal, record, and evolution logs.

## Forbidden scope

No backtesting, brokerage integration, portfolio optimization, model training,
automatic investment advice, remote execution, or P5 features.
