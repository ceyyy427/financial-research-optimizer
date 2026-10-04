-- Finathink P6.6 Strategy Research & Simulation Lab additive migration.
-- Records are immutable provenance envelopes; executable source is never stored
-- in these tables.  JSON values remain text for SQLite/PostgreSQL parity.

CREATE TABLE IF NOT EXISTS p6_6_feature_versions (
    feature_fingerprint TEXT PRIMARY KEY,
    feature_id TEXT NOT NULL,
    version_id TEXT NOT NULL,
    definition TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_6_strategy_versions (
    strategy_fingerprint TEXT PRIMARY KEY,
    strategy_id TEXT NOT NULL,
    version TEXT NOT NULL,
    feature_graph_fingerprint TEXT NOT NULL,
    reviewed INTEGER NOT NULL CHECK (reviewed IN (0,1)),
    specification TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_6_research_runs (
    run_id TEXT PRIMARY KEY,
    strategy_fingerprint TEXT NOT NULL REFERENCES p6_6_strategy_versions(strategy_fingerprint),
    dataset_fingerprint TEXT NOT NULL,
    engine_authority TEXT NOT NULL,
    result_fingerprint TEXT NOT NULL,
    provenance TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_6_paper_runs (
    paper_run_id TEXT PRIMARY KEY,
    strategy_fingerprint TEXT NOT NULL REFERENCES p6_6_strategy_versions(strategy_fingerprint),
    dataset_fingerprint TEXT NOT NULL,
    paper_fingerprint TEXT NOT NULL UNIQUE,
    configuration TEXT NOT NULL,
    limitations TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p6_6_exports (
    package_fingerprint TEXT PRIMARY KEY,
    strategy_fingerprint TEXT NOT NULL REFERENCES p6_6_strategy_versions(strategy_fingerprint),
    manifest TEXT NOT NULL,
    educational_source_fingerprint TEXT NOT NULL,
    created_at TEXT NOT NULL
);
