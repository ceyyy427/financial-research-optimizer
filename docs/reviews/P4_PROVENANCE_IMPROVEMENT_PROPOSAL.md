# P4 Provenance Improvement Proposal

**Status:** Deferred; not implemented in P4
**Reason:** The current P4 record is reproducible for its local inputs, but a
complete answer to “How was this result produced?” needs stronger environment,
source, implementation, and validation identity.

## Observed gap

`ResearchRun` currently records:

- dataset payload, provider, source URL, retrieval metadata, license, and a
  dataset fingerprint;
- factor name, definition, explanation, and limitations;
- method, parameters, creation timestamp, engine version, result, and result
  fingerprint.

It does not yet record a source release/version, immutable source snapshot,
factor implementation revision, runtime dependency versions, or the exact
validation report. These omissions do not invalidate local deterministic
reproduction, but they weaken cross-machine forensic reconstruction.

## Proposed future change

Add a versioned provenance envelope to a future phase or approved P4.x change:

1. `source_version` or immutable snapshot identifier, when a provider exposes
   one;
2. `factor_implementation` containing repository revision/module digest and
   declared factor parameters;
3. `environment` containing Python and relevant package versions;
4. `validation` containing schema/version, warnings, missingness, and the
   validation status used before execution;
5. schema migration rules so old P4 records remain readable and visibly marked
   as legacy provenance.

## Acceptance criteria for a future implementation

- A reviewer can identify the exact dataset snapshot, factor implementation,
  method configuration, runtime, and validation status from a stored record.
- Reproduction distinguishes data drift, code drift, environment drift, and
  result drift with separate errors.
- New fields are included in canonical JSON and fingerprints without storing
  executable code or secrets.
- Existing P4 records round-trip through an explicit migration path.
- Tests cover missing metadata, malformed metadata, migration, and deterministic
  fingerprints.

## Decision

Do not implement this proposal before human approval. It is a research-quality
improvement, not a P4 gate failure.
