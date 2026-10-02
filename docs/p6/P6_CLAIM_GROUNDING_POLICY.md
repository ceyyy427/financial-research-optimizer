# P6 Claim Grounding Policy

Every empirical or numeric statement must resolve to a field in one of:

- `QuantRun` and its normalized backtest or multi-asset result;
- `EvaluationReport`;
- `RegressionResult`;
- `RiskReport`;
- a validated, content-addressed inspection projection.

The grounding record stores `claim_id`, exact claim text, claim kind, source
record ID, source fingerprint, field path, unit, period, and whether the text
is a direct value or an interpretation. Source fingerprints are checked before
rendering. A missing, stale, or mismatched source—or a normalized payload with
no matching approved run identity—makes the claim unavailable;
the explanation must say that the value could not be grounded.

The policy forbids calculating a new metric in the language or explanation
layer, copying a value from user prose, treating a prediction as an outcome,
or suppressing a warning. It also forbids claims that a backtest proves live
profitability, removes all bias, or constitutes investment advice. Limitations
propagate from the source record to every dependent explanation and card.

The low-level claim constructor is intentionally not a source registry:
callers must either pass a normalized source payload for verification or keep
the claim out of an explanation. Only `claims_from_result` (or the verified
constructor path) marks a claim as source-verified.
