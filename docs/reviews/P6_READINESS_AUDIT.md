# P6 Knowledge Engine Readiness Audit

**Result:** CONCEPTUALLY READY; no P6 implementation exists

## Research memory mapping

Current outputs can become future knowledge-graph objects:

| Future node | P4 source |
| --- | --- |
| Question | ResearchRun question and run ID |
| Experiment | Method, parameters, engine version, and timestamps |
| Evidence | Dataset/result payloads, provenance, limitations, and fingerprints |
| Insight | Conclusion and insight text linked to the supporting run |
| Knowledge | A future reviewed claim derived from one or more runs, never directly equated with one result |

Potential typed edges include `QUESTION_TESTED_BY_EXPERIMENT`,
`EXPERIMENT_USED_DATASET`, `EXPERIMENT_PRODUCED_EVIDENCE`,
`EVIDENCE_SUPPORTS_INSIGHT`, and `INSIGHT_REVIEWED_AS_KNOWLEDGE`.

## Can ResearchRun found a Personal Research Graph?

Yes. `run_id`, content fingerprints, question/hypothesis text, dataset
provenance, factor/method metadata, results, conclusions, insights, limitations,
and timestamps provide a stable node payload and lineage anchor.

## Requirements before P6

- Globally stable identifiers and explicit typed-edge schemas.
- Separate evidence, claim, insight, and knowledge statuses.
- Source/version/environment provenance stronger than the P4 minimum.
- Contradiction, supersession, uncertainty, and review-state semantics.
- Schema migration, indexing, query, access-control, export, and backup policy.
- Protection against converting weak or descriptive evidence into asserted
  knowledge.

## Frozen boundary

P6 must consume versioned ResearchRun records through an adapter. It must not
mutate historical evidence, remove limitations, execute stored code, or turn
knowledge retrieval into financial advice.

## Decision

The P4 record is a suitable foundation for a future Personal Research Graph,
but graph storage and knowledge promotion require their own gate. **READY FOR
FUTURE DESIGN ONLY.**
