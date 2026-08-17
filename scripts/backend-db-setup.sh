#!/usr/bin/env bash
#
# Idempotent setup for the backend's database-backed work: bring up Postgres
# and Redis, create the test database, apply migrations, run the suite.
#
#   ./scripts/backend-db-setup.sh            # set up, migrate, test
#   ./scripts/backend-db-setup.sh --no-test  # set up and migrate only
#
# Safe to re-run: every step checks before it acts.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="${REPO_ROOT}/backend"

PGHOST="${POSTGRES_HOST:-localhost}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-vaf}"
PGPASSWORD="${POSTGRES_PASSWORD:-test}"
APP_DB="${POSTGRES_DB:-vaf}"
TEST_DB="${POSTGRES_TEST_DB:-vaf_ws_b_test}"
REDIS_URL="${TEST_REDIS_URL:-redis://localhost:6379/15}"

PYTHON="${PYTHON:-python}"
RUN_TESTS=1
[[ "${1:-}" == "--no-test" ]] && RUN_TESTS=0

export POSTGRES_HOST="$PGHOST" POSTGRES_PORT="$PGPORT" \
       POSTGRES_USER="$PGUSER" POSTGRES_PASSWORD="$PGPASSWORD" \
       POSTGRES_TEST_DB="$TEST_DB" TEST_REDIS_URL="$REDIS_URL"

log() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

# --- 1. Services ------------------------------------------------------------
log "Ensuring Postgres and Redis are up"
if command -v docker >/dev/null 2>&1 && [[ -f "${REPO_ROOT}/docker-compose.yml" ]]; then
  docker compose -f "${REPO_ROOT}/docker-compose.yml" up -d db redis || \
    echo "    compose failed — assuming you are running these yourself"
else
  echo "    docker not available — assuming Postgres and Redis are already running"
fi

# --- 2. Wait for Postgres ---------------------------------------------------
log "Waiting for Postgres at ${PGHOST}:${PGPORT}"
for _ in $(seq 1 30); do
  if "$PYTHON" - <<PY >/dev/null 2>&1; then break; fi
import socket, sys
s = socket.socket()
s.settimeout(1)
try:
    s.connect(("${PGHOST}", ${PGPORT}))
except OSError:
    sys.exit(1)
PY
  sleep 1
done

# --- 3. Databases -----------------------------------------------------------
log "Ensuring databases '${APP_DB}' and '${TEST_DB}' exist"
"$PYTHON" - <<PY
import asyncio, sys

try:
    import asyncpg
except ImportError:
    print("    asyncpg not installed — skipping database creation")
    sys.exit(0)

async def main():
    for db in ("${APP_DB}", "${TEST_DB}"):
        try:
            conn = await asyncpg.connect(
                host="${PGHOST}", port=${PGPORT},
                user="${PGUSER}", password="${PGPASSWORD}", database="postgres",
            )
        except Exception as exc:
            print(f"    could not connect: {exc}")
            return
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = \$1", db
            )
            if exists:
                print(f"    {db}: already present")
            else:
                await conn.execute(f'CREATE DATABASE "{db}"')
                print(f"    {db}: created")
        finally:
            await conn.close()

asyncio.run(main())
PY

# --- 4. Migrations ----------------------------------------------------------
log "Applying migrations to '${APP_DB}'"
(cd "$BACKEND" && POSTGRES_DB="$APP_DB" "$PYTHON" -m alembic upgrade head)

# --- 5. Tests ---------------------------------------------------------------
if [[ "$RUN_TESTS" -eq 1 ]]; then
  log "Running the backend test suite"
  (cd "$BACKEND" && "$PYTHON" -m pytest tests/ -q)
else
  log "Skipping tests (--no-test)"
fi

log "Done"
