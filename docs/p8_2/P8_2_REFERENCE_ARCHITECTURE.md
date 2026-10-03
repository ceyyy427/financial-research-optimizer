# P8.2B Reference Architecture

`ReferenceRecord` is the local metadata contract for a source-backed
educational claim. It distinguishes reference type and role, stores authors,
year, publisher, DOI, legal URL, provenance, notes, and optional open-access
URL. DOI normalization is deterministic and duplicate IDs/DOIs are rejected.

`LocalReferenceCache` is the offline source of truth after a metadata record is
validated. A future Crossref adapter may resolve metadata on demand and write
only normalized records; it must never cache full-text papers or invent missing
fields. Citation output is available as BibTeX and CSL JSON so a learner can
take the literature with them.
