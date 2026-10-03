-- P7 private continuity and evidence-driven community. Additive and portable
-- across SQLite tests and the PostgreSQL target. Payloads are JSON text; all
-- writes remain parameterized in the repository.

CREATE TABLE IF NOT EXISTS p7_principals (
    principal_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','suspended','deleted')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p7_sessions (
    session_id TEXT PRIMARY KEY,
    principal_id TEXT NOT NULL REFERENCES p7_principals(principal_id),
    created_at TEXT NOT NULL,
    expires_at TEXT,
    revoked INTEGER NOT NULL DEFAULT 0 CHECK (revoked IN (0,1))
);

CREATE TABLE IF NOT EXISTS p7_artifact_links (
    link_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id),
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    allowed_fields TEXT NOT NULL,
    current_fingerprint TEXT NOT NULL,
    code_commit TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (owner_id, source_kind, source_id)
);

CREATE TABLE IF NOT EXISTS p7_personal_nodes (
    node_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    node_type TEXT NOT NULL CHECK (node_type IN ('concept','claim','evidence','event','question','hypothesis','research','quant_run','strategy','feature','paper_run','learning_card','misconception','review_item','note')),
    title TEXT NOT NULL,
    payload TEXT NOT NULL,
    privacy_scope TEXT NOT NULL DEFAULT 'PRIVATE' CHECK (privacy_scope = 'PRIVATE'),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p7_personal_edges (
    edge_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    from_node_id TEXT NOT NULL REFERENCES p7_personal_nodes(node_id) ON DELETE CASCADE,
    to_node_id TEXT NOT NULL REFERENCES p7_personal_nodes(node_id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL CHECK (relation_type IN ('LEARNED','USED','QUESTIONED','TESTED','CONFUSED_WITH','CORRECTED_BY','DERIVED_FROM','RELATED_TO','NEEDS_REVIEW','MASTERED_EVIDENCE','SUPPORTED_BY')),
    evidence_ids TEXT NOT NULL,
    UNIQUE (owner_id, from_node_id, to_node_id, relation_type)
);

CREATE TABLE IF NOT EXISTS p7_mastery_evidence (
    evidence_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES p7_personal_nodes(node_id) ON DELETE CASCADE,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('quiz_response','prediction_response','explanation','research_use','strategy_use','misconception_correction','transfer_question','repeat_exposure')),
    evidence_reference TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('correct','incorrect','neutral','corrected')),
    observed_at TEXT NOT NULL,
    details TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p7_mastery_states (
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES p7_personal_nodes(node_id) ON DELETE CASCADE,
    state TEXT NOT NULL CHECK (state IN ('NEW','EXPOSED','DEVELOPING','APPLIED','ROBUST','NEEDS_REVIEW')),
    evidence_count INTEGER NOT NULL CHECK (evidence_count >= 0),
    evidence_ids TEXT NOT NULL,
    explanation TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (owner_id, concept_id)
);

CREATE TABLE IF NOT EXISTS p7_learning_threads (
    thread_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','completed','archived')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p7_learning_thread_items (
    thread_id TEXT NOT NULL REFERENCES p7_learning_threads(thread_id) ON DELETE CASCADE,
    node_id TEXT NOT NULL REFERENCES p7_personal_nodes(node_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position >= 0),
    PRIMARY KEY (thread_id, node_id),
    UNIQUE (thread_id, position)
);

CREATE TABLE IF NOT EXISTS p7_history_entries (
    history_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    limitations TEXT NOT NULL,
    UNIQUE (owner_id, source_kind, source_id, event_type)
);

CREATE TABLE IF NOT EXISTS p7_saved_objects (
    saved_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (owner_id, source_kind, source_id)
);

CREATE TABLE IF NOT EXISTS p7_rooms (
    room_id TEXT PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','archived')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p7_room_members (
    room_id TEXT NOT NULL REFERENCES p7_rooms(room_id) ON DELETE CASCADE,
    principal_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner','member','moderator')),
    status TEXT NOT NULL CHECK (status IN ('active','removed')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (room_id, principal_id)
);

CREATE TABLE IF NOT EXISTS p7_projections (
    projection_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    fields TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK (visibility IN ('PRIVATE','SHARED_ROOM','SHARED_GROUP','PUBLIC')),
    room_id TEXT REFERENCES p7_rooms(room_id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK (status IN ('DRAFT','ACTIVE','REVOKED','STALE')),
    version INTEGER NOT NULL CHECK (version >= 1),
    payload TEXT NOT NULL,
    limitations TEXT NOT NULL DEFAULT '[]',
    consented_at TEXT,
    revoked_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (owner_id, source_kind, source_id, version)
);

CREATE TABLE IF NOT EXISTS p7_posts (
    post_id TEXT PRIMARY KEY,
    room_id TEXT NOT NULL REFERENCES p7_rooms(room_id) ON DELETE CASCADE,
    author_id TEXT NOT NULL REFERENCES p7_principals(principal_id),
    claim_type TEXT NOT NULL CHECK (claim_type IN ('FACT','INTERPRETATION','HYPOTHESIS','QUANT_FINDING','UNKNOWN','LIMITATION')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','removed')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p7_comments (
    comment_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL REFERENCES p7_posts(post_id) ON DELETE CASCADE,
    author_id TEXT NOT NULL REFERENCES p7_principals(principal_id),
    body TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','removed')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS p7_projection_attachments (
    attachment_id TEXT PRIMARY KEY,
    post_id TEXT NOT NULL REFERENCES p7_posts(post_id) ON DELETE CASCADE,
    projection_id TEXT NOT NULL REFERENCES p7_projections(projection_id),
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (post_id, projection_id)
);

CREATE TABLE IF NOT EXISTS p7_audit_events (
    audit_id TEXT PRIMARY KEY,
    principal_id TEXT REFERENCES p7_principals(principal_id),
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_p7_nodes_owner ON p7_personal_nodes(owner_id);
CREATE INDEX IF NOT EXISTS idx_p7_history_owner_time ON p7_history_entries(owner_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_p7_projection_status ON p7_projections(status, visibility);
CREATE INDEX IF NOT EXISTS idx_p7_posts_room ON p7_posts(room_id, created_at);
CREATE INDEX IF NOT EXISTS idx_p7_mastery_owner ON p7_mastery_states(owner_id, state);

-- Explicit continuity records keep misconception lifecycle and strategy
-- provenance inspectable without turning them into opaque user profiles.
CREATE TABLE IF NOT EXISTS p7_misconceptions (
    misconception_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    concept_id TEXT NOT NULL REFERENCES p7_personal_nodes(node_id) ON DELETE CASCADE,
    observed_statement TEXT NOT NULL,
    correction TEXT NOT NULL,
    evidence_reference TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    corrected_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('OPEN','CORRECTED')),
    related_concept_ids TEXT NOT NULL DEFAULT '[]',
    learning_interactions TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS p7_strategy_versions (
    strategy_version_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES p7_principals(principal_id) ON DELETE CASCADE,
    strategy_id TEXT NOT NULL,
    strategy_fingerprint TEXT NOT NULL,
    feature_fingerprint TEXT,
    backtest_fingerprint TEXT,
    oos_fingerprint TEXT,
    paper_fingerprint TEXT,
    limitations TEXT NOT NULL DEFAULT '[]',
    code_commit TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (owner_id, strategy_id, strategy_fingerprint)
);

CREATE INDEX IF NOT EXISTS idx_p7_misconception_owner ON p7_misconceptions(owner_id, status);
CREATE INDEX IF NOT EXISTS idx_p7_strategy_history_owner ON p7_strategy_versions(owner_id, created_at);
