-- Finathink P6.5 Understanding Engine migration.
-- JSON values remain text so the same integrity constraints can be replayed in
-- SQLite tests; PostgreSQL deployments may promote the columns to JSONB under
-- a future reviewed migration.

CREATE TABLE IF NOT EXISTS p6_5_sources (
    source_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    publisher TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('TIER_0','TIER_1','TIER_2','TIER_3')),
    canonical_url TEXT NOT NULL,
    underlying_source TEXT NOT NULL,
    owner TEXT NOT NULL,
    access_method TEXT NOT NULL,
    usage_conditions TEXT NOT NULL,
    authentication TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('ADMIT_AUTHORITATIVE','ADMIT_PROVIDER','ADMIT_RESEARCH_ONLY','DISCOVERY_ONLY','DEFER','REJECT')),
    source_fingerprint TEXT NOT NULL UNIQUE,
    admitted_at TEXT
);

CREATE TABLE IF NOT EXISTS p6_5_endpoints (
    endpoint_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES p6_5_sources(source_id),
    url TEXT NOT NULL,
    method TEXT NOT NULL CHECK (method IN ('GET','POST')),
    content_type TEXT NOT NULL,
    rate_limit TEXT NOT NULL,
    historical_support INTEGER NOT NULL CHECK (historical_support IN (0,1)),
    revision_support TEXT NOT NULL,
    available_at_semantics TEXT NOT NULL,
    active INTEGER NOT NULL CHECK (active IN (0,1)),
    UNIQUE (source_id, url, method)
);

CREATE TABLE IF NOT EXISTS p6_5_releases (
    release_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES p6_5_sources(source_id),
    endpoint_id TEXT NOT NULL REFERENCES p6_5_endpoints(endpoint_id),
    event_type TEXT NOT NULL,
    reference_period TEXT NOT NULL,
    published_at TEXT NOT NULL,
    available_at TEXT,
    release_url TEXT NOT NULL,
    schedule_fingerprint TEXT,
    UNIQUE (source_id, event_type, reference_period, release_url)
);

CREATE TABLE IF NOT EXISTS p6_5_artifacts (
    artifact_id TEXT PRIMARY KEY,
    payload_hash TEXT NOT NULL UNIQUE,
    storage_path TEXT NOT NULL,
    byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_5_captures (
    capture_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES p6_5_sources(source_id),
    endpoint_id TEXT NOT NULL REFERENCES p6_5_endpoints(endpoint_id),
    request_fingerprint TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    first_observed_at TEXT NOT NULL,
    status INTEGER NOT NULL CHECK (status BETWEEN 100 AND 599),
    content_type TEXT NOT NULL,
    relevant_headers TEXT NOT NULL,
    raw_artifact_id TEXT NOT NULL REFERENCES p6_5_artifacts(artifact_id),
    payload_hash TEXT NOT NULL REFERENCES p6_5_artifacts(payload_hash),
    parser_version TEXT NOT NULL,
    UNIQUE (source_id, request_fingerprint, payload_hash)
);

CREATE TABLE IF NOT EXISTS p6_5_observations (
    observation_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES p6_5_sources(source_id),
    series_id TEXT NOT NULL,
    reference_period TEXT NOT NULL,
    dimensions TEXT NOT NULL,
    UNIQUE (source_id, series_id, reference_period, dimensions)
);

CREATE TABLE IF NOT EXISTS p6_5_observation_versions (
    version_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES p6_5_observations(observation_id),
    value DOUBLE PRECISION NOT NULL,
    unit TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    published_at TEXT,
    available_at TEXT,
    retrieved_at TEXT NOT NULL,
    capture_id TEXT NOT NULL REFERENCES p6_5_captures(capture_id),
    revision_status TEXT NOT NULL CHECK (revision_status IN ('ORIGINAL','REVISED','SUPERSEDED','UNRESOLVED_REVISION')),
    supersedes_version_id TEXT REFERENCES p6_5_observation_versions(version_id),
    footnotes TEXT NOT NULL,
    UNIQUE (observation_id, version_id)
);

CREATE TABLE IF NOT EXISTS p6_5_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES p6_5_sources(source_id),
    reference_period TEXT NOT NULL,
    occurred_at TEXT,
    effective_at TEXT,
    published_at TEXT NOT NULL,
    available_at TEXT,
    revision_status TEXT NOT NULL CHECK (revision_status IN ('ORIGINAL','REVISED','SUPERSEDED','UNRESOLVED_REVISION')),
    fingerprint TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS p6_5_event_observations (
    event_id TEXT NOT NULL REFERENCES p6_5_events(event_id),
    observation_id TEXT NOT NULL REFERENCES p6_5_observations(observation_id),
    PRIMARY KEY (event_id, observation_id)
);

CREATE TABLE IF NOT EXISTS p6_5_evidence (
    evidence_id TEXT PRIMARY KEY,
    evidence_type TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES p6_5_sources(source_id),
    capture_id TEXT REFERENCES p6_5_captures(capture_id),
    reference TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('DIRECT_SOURCE','DERIVED_FROM_SOURCE','QUANT_SUPPORTED','THEORY_SUPPORTED','PARTIALLY_SUPPORTED','INSUFFICIENT_EVIDENCE')),
    scope TEXT NOT NULL,
    limitations TEXT NOT NULL,
    source_fingerprint TEXT
);

CREATE TABLE IF NOT EXISTS p6_5_event_evidence (
    event_id TEXT NOT NULL REFERENCES p6_5_events(event_id),
    evidence_id TEXT NOT NULL REFERENCES p6_5_evidence(evidence_id),
    PRIMARY KEY (event_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS p6_5_claims (
    claim_id TEXT PRIMARY KEY,
    claim_type TEXT NOT NULL CHECK (claim_type IN ('FACT','INTERPRETATION','HYPOTHESIS','QUANT_FINDING','UNKNOWN','LIMITATION')),
    text TEXT NOT NULL,
    evidence_status TEXT NOT NULL CHECK (evidence_status IN ('DIRECT_SOURCE','DERIVED_FROM_SOURCE','QUANT_SUPPORTED','THEORY_SUPPORTED','PARTIALLY_SUPPORTED','INSUFFICIENT_EVIDENCE')),
    source_fingerprint TEXT,
    source_verified INTEGER NOT NULL CHECK (source_verified IN (0,1)),
    limitations TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_5_claim_evidence (
    claim_id TEXT NOT NULL REFERENCES p6_5_claims(claim_id),
    evidence_id TEXT NOT NULL REFERENCES p6_5_evidence(evidence_id),
    support_type TEXT NOT NULL CHECK (support_type IN ('DIRECT_SOURCE','DERIVED_FROM_SOURCE','QUANT_SUPPORTED','THEORY_SUPPORTED','PARTIALLY_SUPPORTED','INSUFFICIENT_EVIDENCE')),
    scope TEXT NOT NULL,
    limitations TEXT NOT NULL,
    PRIMARY KEY (claim_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS p6_5_concepts (
    concept_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,
    formula TEXT NOT NULL,
    evidence_ids TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_5_concept_relations (
    relation_id TEXT PRIMARY KEY,
    from_concept_id TEXT NOT NULL REFERENCES p6_5_concepts(concept_id),
    to_concept_id TEXT NOT NULL REFERENCES p6_5_concepts(concept_id),
    relation_type TEXT NOT NULL CHECK (relation_type IN ('ECONOMIC_MECHANISM','SUPPORTED_RELATIONSHIP','HISTORICAL_ASSOCIATION','HYPOTHESIS')),
    evidence_status TEXT NOT NULL CHECK (evidence_status IN ('DIRECT_SOURCE','DERIVED_FROM_SOURCE','QUANT_SUPPORTED','THEORY_SUPPORTED','PARTIALLY_SUPPORTED','INSUFFICIENT_EVIDENCE')),
    evidence_ids TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_5_hypotheses (
    hypothesis_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES p6_5_events(event_id),
    statement TEXT NOT NULL,
    null_statement TEXT NOT NULL,
    factor TEXT NOT NULL,
    benchmark TEXT NOT NULL,
    evaluation_boundary TEXT NOT NULL,
    limitations TEXT NOT NULL,
    fingerprint TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS p6_5_explanations (
    explanation_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES p6_5_events(event_id),
    asked TEXT NOT NULL,
    tested TEXT NOT NULL,
    what_happened TEXT NOT NULL,
    what_changed TEXT NOT NULL,
    why_it_may_matter TEXT NOT NULL,
    what_we_know TEXT NOT NULL,
    evidence_suggests TEXT NOT NULL,
    plausible TEXT NOT NULL,
    unknown TEXT NOT NULL,
    what_would_change_view TEXT NOT NULL,
    what_to_watch_next TEXT NOT NULL,
    limitations TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_5_learning_refs (
    learning_ref_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL REFERENCES p6_5_events(event_id),
    evidence_id TEXT NOT NULL REFERENCES p6_5_evidence(evidence_id),
    concept_id TEXT REFERENCES p6_5_concepts(concept_id),
    card_fingerprint TEXT NOT NULL,
    user_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_5_observation_conflicts (
    conflict_id TEXT PRIMARY KEY,
    observation_id TEXT NOT NULL REFERENCES p6_5_observations(observation_id),
    version_a TEXT NOT NULL REFERENCES p6_5_observation_versions(version_id),
    value_a DOUBLE PRECISION NOT NULL,
    version_b TEXT NOT NULL REFERENCES p6_5_observation_versions(version_id),
    value_b DOUBLE PRECISION NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'SOURCE_CONFLICT')
);

CREATE INDEX IF NOT EXISTS idx_p6_5_observation_available ON p6_5_observation_versions (available_at);
CREATE INDEX IF NOT EXISTS idx_p6_5_event_period ON p6_5_events (source_id, reference_period);
CREATE INDEX IF NOT EXISTS idx_p6_5_claim_evidence ON p6_5_claim_evidence (evidence_id, claim_id);
CREATE INDEX IF NOT EXISTS idx_p6_5_capture_first_observed ON p6_5_captures (first_observed_at);
