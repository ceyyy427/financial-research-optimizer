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
MIGRATION="${REPO_ROOT}/migrations/001_p6_5_understanding.sql"
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

[[ -f "${MIGRATION}" ]] || fail "migration not found: ${MIGRATION}"
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
    if docker exec "${CONTAINER_NAME}" pg_isready -U postgres -d "${DATABASE_NAME}" >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 1
done
[[ "${ready}" == 1 ]] || fail "PostgreSQL did not become ready within 60 seconds"

printf 'Applying %s...\n' "${MIGRATION}"
docker exec -i "${CONTAINER_NAME}" psql \
    --username=postgres \
    --dbname="${DATABASE_NAME}" \
    --set=ON_ERROR_STOP=1 \
    < "${MIGRATION}" >/dev/null

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
        'p6_5_observation_conflicts'
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
        'idx_p6_5_capture_first_observed'
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
END
$$;

SELECT 'P6.5_POSTGRES_SCHEMA_PASS';
SQL

printf 'P6.5 PostgreSQL verification: PASS (container will be removed: %s)\n' "${CONTAINER_NAME}"
