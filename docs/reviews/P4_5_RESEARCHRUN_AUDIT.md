# P4.5 ResearchRun Domain Audit

**Result:** PASS

## Domain coverage

| Required concept | ResearchRun evidence |
| --- | --- |
| Question | Required non-empty `question` text. |
| Hypothesis | Required non-empty `hypothesis` text. |
| Dataset | Canonical columns, dated records, provenance, and content fingerprint. |
| Factor | Name, definition, explanation, limitations, and the P3 computation used at execution time. |
| Method | Required method name; P4 uses `information_coefficient`. |
| Parameters | Canonical method configuration, currently horizon and factor-shift periods. |
| Result | Coverage and information coefficient plus a result fingerprint. |
| Conclusion | Required researcher-authored interpretation. |
| Insight | Required researcher-authored research-memory statement. |
| Limitations | Factor limitations plus experiment-level descriptive/no-advice warning. |

The record also carries `run_id`, `created_at`, `engine_version`, and schema
version on serialization.

## Four audit questions

### What did the user want to understand?

Yes. `question` records the curiosity and `hypothesis` records the proposed
relationship before the result is interpreted.

### How was it tested?

Yes for the P4 local workflow. The run records the complete dataset payload,
factor identity/definition, method, parameters, creation time, and engine
version. The factor implementation itself is not serialized or executed from
the record.

### What evidence was produced?

Yes. The run stores the normalized data snapshot, dataset fingerprint, result
payload, result fingerprint, and limitations. The result is descriptive
evidence; it is not a trading recommendation or causal proof.

### What was learned?

Yes. `conclusion` and `insight` make human interpretation explicit. P4 stores
these statements but correctly does not claim to validate their scientific
quality automatically.

## Validation evidence

- Required narrative fields reject empty values.
- Canonical JSON round-trips back to an equal ResearchRun.
- A tampered dataset payload fails fingerprint validation.
- Non-finite result metrics are normalized to JSON `null`.
- Dataset and result fingerprints are stable for identical canonical inputs.

Relevant tests are in `tests/experiments/test_models.py` and
`tests/experiments/test_engine.py`.

## Known limitations

- Source release/version, runtime dependency versions, validation reports, and
  factor implementation digests are not first-class fields.
- Factor parameters such as a momentum window are embedded in the factor name
  and definition rather than a separate structured mapping.
- `from_dict` verifies required keys and fingerprints but is permissive about
  several individual field types.
- Reproduction replays stored method parameters; it does not accept an
  alternate candidate parameter map for sensitivity comparison.

These limitations are documented in the provenance improvement proposal and
do not prevent the record from answering the four P4 research questions.

## Decision

ResearchRun is a stable core object for Finahinking research memory. **PASS.**
