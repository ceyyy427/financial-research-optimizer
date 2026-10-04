# P6.6 Reproducibility Review

Feature definitions, graphs, reviewed strategy versions, IR nodes,
configuration mappings, dataset fingerprints, P5/P5.5 result fingerprints,
PaperRun fingerprints, drift reports, learning interactions, and export files
are content-addressed. Replay uses deterministic fixtures, explicit cost
models, next-period timing, and an approved dataset reference.

The P5.5 panel artifact now retains the complete immutable panel dataset
records in `dataset_artifact` in addition to the dataset fingerprint. The
export package records strategy/graph/source/result references and a manifest
hash. `PaperRun.from_dict` rejects tampered payload fingerprints.

The code commit and dependency versions remain in the existing QuantRun and
ResearchRun provenance envelopes. Timestamps are pinned to the dataset as-of
boundary in fixtures; live clocks, live feeds, and network retries are not
part of the validation claim.

## Review result

PASS for deterministic replay and bounded export. A future provider-backed
workflow must add source admission and immutable record storage before it can
claim replayability.
