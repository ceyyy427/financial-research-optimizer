# P7 Data Quality Review

P7 stores typed records with database checks, foreign keys, deterministic JSON,
source fingerprints, and UTC timestamps. Mastery state is recomputed from the
ordered evidence table and includes evidence ids in its explanation. Projection
quality is checked at write time (owner, current fingerprint, allow-list,
explicit consent) and at refresh time (stale-source detection).

Known limitations: SQLite is a deterministic local adapter, not the production
concurrency proof; moderation and duplicate-content policy are not yet
implemented; source freshness is only as strong as the upstream P6 artifact
fingerprint. These limitations are surfaced rather than hidden.
