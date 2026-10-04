#!/usr/bin/env bash
# Validate the P6.5 migration against a disposable PostgreSQL 16 container.
#
# This is a verification helper, not an environment reset command.  It refuses
# to touch an already-existing container with the chosen name and only removes
# the container that it created itself.  No host database, volume, or source
# file is deleted.

set -Eeuo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)"
MIGRATIONS=(
    "${REPO_ROOT}/migrations/001_p6_5_understanding.sql"
    "${REPO_ROOT}/migrations/002_p6_6_strategy_lab.sql"
    "${REPO_ROOT}/migrations/003_p7_personal_community.sql"
)
CONTAINER_NAME="${P65_POSTGRES_CONTAINER:-finahinking-p65-postgres-verify}"
DATABASE_NAME="${P65_POSTGRES_DATABASE:-finahinking_p65_verify}"
POSTGRES_PASSWORD_VALUE="${P65_POSTGRES_PASSWORD:-finahinking-p65-local-only}"
CREATED=0

fail() {
    printf 'P6.5 PostgreSQL verification: FAIL: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    if [[ "${CREATED}" == 1 ]]; then
        docker rm -f -- "${CONTAINER_NAME}" >/dev/null 2>&1 || true
    fi
}
trap cleanup EXIT INT TERM

for migration in "${MIGRATIONS[@]}"; do
    [[ -f "${migration}" ]] || fail "migration not found: ${migration}"
done
command -v docker >/dev/null 2>&1 || fail "docker is required (no host database is modified)"

if [[ ! "${CONTAINER_NAME}" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$ ]]; then
    fail "container name contains unsafe characters"
fi
if [[ ! "${DATABASE_NAME}" =~ ^[a-zA-Z_][a-zA-Z0-9_]{0,62}$ ]]; then
    fail "database name contains unsafe characters"
fi

if docker ps -a --format '{{.Names}}' | grep -Fx -- "${CONTAINER_NAME}" >/dev/null 2>&1; then
    fail "container name already exists; choose P65_POSTGRES_CONTAINER rather than modifying it"
fi

printf 'Starting disposable %s from postgres:16-alpine...\n' "${CONTAINER_NAME}"
docker run --pull=missing --detach --rm \
    --name "${CONTAINER_NAME}" \
    --env "POSTGRES_PASSWORD=${POSTGRES_PASSWORD_VALUE}" \
    --env "POSTGRES_DB=${DATABASE_NAME}" \
    postgres:16-alpine >/dev/null
CREATED=1

ready=0
for _attempt in $(seq 1 60); do
    # pg_isready can report a ready server while initdb is still creating
    # POSTGRES_DB. Probe the target database with psql so migrations never race
    # the image's initialization scripts.
    if docker exec "${CONTAINER_NAME}" psql \
        --username=postgres \
        --dbname="${DATABASE_NAME}" \
        --command='SELECT 1' >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
done
[[ "${ready}" == 1 ]] || fail "PostgreSQL did not become ready within 60 seconds"

for migration in "${MIGRATIONS[@]}"; do
    printf 'Applying %s...\n' "${migration}"
    docker exec -i "${CONTAINER_NAME}" psql \
        --username=postgres \
        --dbname="${DATABASE_NAME}" \
        --set=ON_ERROR_STOP=1 \
        < "${migration}" >/dev/null
done

printf 'Checking tables, constraints, and indexes...\n'
docker exec -i "${CONTAINER_NAME}" psql \
    --username=postgres \
    --dbname="${DATABASE_NAME}" \
    --set=ON_ERROR_STOP=1 \
    --tuples-only --no-align <<'SQL'
DO $$
DECLARE
    required_table text;
    required_tables constant text[] := ARRAY[
        'p6_5_sources', 'p6_5_endpoints', 'p6_5_releases',
        'p6_5_artifacts', 'p6_5_captures', 'p6_5_observations',
        'p6_5_observation_versions', 'p6_5_events',
        'p6_5_event_observations', 'p6_5_event_evidence',
        'p6_5_evidence', 'p6_5_claims', 'p6_5_claim_evidence',
        'p6_5_concepts', 'p6_5_concept_relations', 'p6_5_hypotheses',
        'p6_5_explanations', 'p6_5_learning_refs',
        'p6_5_observation_conflicts',
        'p7_principals', 'p7_sessions', 'p7_artifact_links',
        'p7_personal_nodes', 'p7_personal_edges', 'p7_mastery_evidence',
        'p7_mastery_states', 'p7_learning_threads',
        'p7_learning_thread_items', 'p7_history_entries', 'p7_saved_objects',
        'p7_rooms', 'p7_room_members', 'p7_projections', 'p7_posts',
        'p7_comments', 'p7_projection_attachments', 'p7_audit_events'
        ,'p7_misconceptions', 'p7_strategy_versions'
    ];
BEGIN
    FOREACH required_table IN ARRAY required_tables LOOP
        IF to_regclass(required_table) IS NULL THEN
            RAISE EXCEPTION 'required table is missing: %', required_table;
        END IF;
    END LOOP;
END
$$;

DO $$
DECLARE
    required_index text;
BEGIN
    FOREACH required_index IN ARRAY ARRAY[
        'idx_p6_5_observation_available',
        'idx_p6_5_event_period',
        'idx_p6_5_claim_evidence',
        'idx_p6_5_capture_first_observed',
        'idx_p7_nodes_owner', 'idx_p7_history_owner_time',
        'idx_p7_projection_status', 'idx_p7_posts_room', 'idx_p7_mastery_owner',
        'idx_p7_misconception_owner', 'idx_p7_strategy_history_owner'
    ] LOOP
        IF to_regclass(required_index) IS NULL THEN
            RAISE EXCEPTION 'required index is missing: %', required_index;
        END IF;
    END LOOP;
END
$$;

DO $$
DECLARE
    foreign_key_count integer;
    check_count integer;
BEGIN
    SELECT count(*) INTO foreign_key_count
      FROM pg_constraint
     WHERE contype = 'f'
       AND conrelid IN (
           'p6_5_endpoints'::regclass,
           'p6_5_captures'::regclass,
           'p6_5_observation_versions'::regclass,
           'p6_5_claim_evidence'::regclass
       );
    IF foreign_key_count < 4 THEN
        RAISE EXCEPTION 'expected foreign-key constraints are missing (found %)', foreign_key_count;
    END IF;

    SELECT count(*) INTO check_count
      FROM pg_constraint
      WHERE contype = 'c'
      AND conrelid = 'p6_5_sources'::regclass;
    IF check_count < 2 THEN
        RAISE EXCEPTION 'source tier/admission checks are missing (found %)', check_count;
    END IF;

    SELECT count(*) INTO foreign_key_count
      FROM pg_constraint
     WHERE contype = 'f'
       AND conrelid = 'p7_projections'::regclass;
    IF foreign_key_count < 2 THEN
        RAISE EXCEPTION 'P7 room projection foreign-key constraint is missing';
    END IF;
END
$$;

SELECT 'P6.5_POSTGRES_SCHEMA_PASS';
SQL

printf 'P6.5 PostgreSQL verification: PASS (container will be removed: %s)\n' "${CONTAINER_NAME}"
