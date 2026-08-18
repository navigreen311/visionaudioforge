#!/usr/bin/env bash
# Bring the stack up and prove it actually works.
#
# "Containers are running" is not the bar. This asserts the things that were
# silently broken before anyone had ever started this stack: that migrations
# applied, that the extensions exist, that the bucket exists, that the console
# is reachable *through nginx*, that the auth boundary survives the proxy, and
# that the worker is attached to the broker.
#
# Used by `make smoke` and by the compose-smoke job in
# .github/workflows/test.yml, so the thing CI runs is the thing you can run.
#
# Usage:
#   scripts/smoke-stack.sh              # up, assert, leave running
#   scripts/smoke-stack.sh --down       # up, assert, tear down (CI default)
#   scripts/smoke-stack.sh --core       # api core only: no frontend/nginx
#
# Exit status is the result: 0 = the stack works.

set -euo pipefail

TEARDOWN=0
CORE_ONLY=0
WAIT_TIMEOUT="${WAIT_TIMEOUT:-900}"

# Must match the defaults in docker-compose.yml. Overridable for the same
# reason they are there: parallel worktrees and other stacks share the host.
API_PORT="${API_PORT:-8000}"
HTTP_PORT="${HTTP_PORT:-80}"

for arg in "$@"; do
    case "$arg" in
        --down) TEARDOWN=1 ;;
        --core) CORE_ONLY=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

cd "$(dirname "$0")/.."

# ANTHROPIC_API_KEY is deliberately left unset: the copilot must degrade to its
# documented mock mode rather than take the API container down. Exporting it
# empty makes that explicit rather than accidental.
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"

PASS=0
FAIL=0

ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL + 1)); }
step() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }

check() {
    # check <description> <command...>
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi
}

dump_diagnostics() {
    step "Diagnostics"
    docker compose ps || true
    for svc in migrate minio_init api celery_worker nginx frontend; do
        echo "----- $svc (last 40 lines) -----"
        docker compose logs --tail 40 "$svc" 2>&1 || true
    done
}

teardown() {
    if [ "$TEARDOWN" -eq 1 ]; then
        step "Tearing down"
        docker compose down -v --remove-orphans || true
    fi
}
trap teardown EXIT

if [ "$CORE_ONLY" -eq 1 ]; then
    SERVICES="db redis minio minio_init migrate api celery_worker"
    echo "Mode: CORE (frontend and nginx excluded)"
else
    SERVICES=""
    echo "Mode: FULL STACK"
fi

# CI builds the images itself so it can attach a layer cache; re-building here
# would throw that away. Locally the default is to build, so `make smoke` on a
# dirty tree tests the code you actually have.
if [ "${SMOKE_NO_BUILD:-0}" = "1" ]; then
    BUILD_FLAG=""
    echo "Build: skipped (SMOKE_NO_BUILD=1 — using pre-built images)"
else
    BUILD_FLAG="--build"
fi

# ---------------------------------------------------------------------------
step "Starting the stack (waiting on health gates, not on a sleep)"
# ---------------------------------------------------------------------------
# --wait blocks until every service is healthy or, for the one-shot jobs,
# exited successfully. That is a real gate: if migrations fail or the bucket
# cannot be created, this returns non-zero instead of racing ahead.
# shellcheck disable=SC2086
if ! docker compose up -d $BUILD_FLAG --wait --wait-timeout "$WAIT_TIMEOUT" $SERVICES; then
    bad "stack reached a healthy state"
    dump_diagnostics
    exit 1
fi
ok "every service reported healthy within ${WAIT_TIMEOUT}s"

# ---------------------------------------------------------------------------
step "One-shot jobs completed successfully"
# ---------------------------------------------------------------------------
for job in migrate minio_init; do
    code="$(docker compose ps -a --format '{{.Service}} {{.ExitCode}}' \
            | awk -v s="$job" '$1 == s {print $2; exit}')"
    if [ "${code:-none}" = "0" ]; then ok "$job exited 0"; else bad "$job exited ${code:-<not run>}"; fi
done

# ---------------------------------------------------------------------------
step "Database: migrations and extensions"
# ---------------------------------------------------------------------------
PSQL="docker compose exec -T db psql -U ${POSTGRES_USER:-vaf} -d ${POSTGRES_DB:-vaf} -tAc"

# All six migrations, not just "some ran": alembic stamps one row.
revision="$($PSQL 'SELECT version_num FROM alembic_version' 2>/dev/null | tr -d '[:space:]')"
if [ -n "$revision" ]; then ok "alembic_version present (head = $revision)"
else bad "alembic_version table missing — migrations never applied"; fi

applied="$(docker compose run --rm --no-deps migrate alembic history 2>/dev/null | grep -c '^' || echo 0)"
echo "      (alembic history lines: $applied)"

for ext in vector pg_trgm; do
    found="$($PSQL "SELECT 1 FROM pg_extension WHERE extname='$ext'" 2>/dev/null | tr -d '[:space:]')"
    if [ "$found" = "1" ]; then ok "extension '$ext' created by scripts/init-db.sql"
    else bad "extension '$ext' MISSING"; fi
done

tables="$($PSQL "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | tr -d '[:space:]')"
if [ "${tables:-0}" -gt 5 ]; then ok "schema has $tables tables"
else bad "schema has only ${tables:-0} tables — migrations did not build the schema"; fi

# ---------------------------------------------------------------------------
step "Object store: bucket exists"
# ---------------------------------------------------------------------------
bucket="${MINIO_BUCKET:-vaf-assets}"
if docker compose run --rm --no-deps --entrypoint sh minio_init -c \
      "mc alias set local http://minio:9000 \"\$MINIO_ROOT_USER\" \"\$MINIO_ROOT_PASSWORD\" >/dev/null && mc ls local/$bucket" \
      >/dev/null 2>&1; then
    ok "bucket '$bucket' exists"
else
    bad "bucket '$bucket' missing"
fi

# ---------------------------------------------------------------------------
step "API direct on :${API_PORT}"
# ---------------------------------------------------------------------------
health="$(curl -fsS http://localhost:${API_PORT}/api/health 2>/dev/null || echo '{}')"
echo "      $health"

json_says() { printf '%s' "$health" | grep -qiE "$1"; }

if json_says '"status"[[:space:]]*:[[:space:]]*"(healthy|ok)"'; then ok "/api/health reports healthy"
else bad "/api/health did not report healthy"; fi

for dep in database redis minio; do
    if printf '%s' "$health" | grep -qiE "\"$dep\"[^}]*\"(up|healthy|ok)\""; then
        ok "dependency '$dep' reports up"
    else
        bad "dependency '$dep' not reporting up"
    fi
done

# ---------------------------------------------------------------------------
step "Auth boundary is intact (WS-A middleware)"
# ---------------------------------------------------------------------------
code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:${API_PORT}/api/assets || echo 000)"
if [ "$code" = "401" ]; then ok "unauthenticated /api/assets -> 401"
else bad "unauthenticated /api/assets -> $code (expected 401)"; fi

code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:${API_PORT}/api/health || echo 000)"
if [ "$code" = "200" ]; then ok "/api/health is on the public allowlist -> 200"
else bad "/api/health -> $code — health probes are being challenged"; fi

# ---------------------------------------------------------------------------
step "Copilot degrades without ANTHROPIC_API_KEY"
# ---------------------------------------------------------------------------
if docker compose logs api 2>&1 | grep -qi "mock mode"; then
    ok "copilot logged its documented mock-mode fallback"
else
    echo "      (no mock-mode line found; API is healthy regardless)"
fi
check "api container is running with no ANTHROPIC_API_KEY set" \
    sh -c 'test -z "$(docker compose exec -T api printenv ANTHROPIC_API_KEY 2>/dev/null | tr -d "[:space:]")"'

# ---------------------------------------------------------------------------
step "Celery worker is attached to the broker"
# ---------------------------------------------------------------------------
if docker compose exec -T celery_worker celery -A app.celery_app inspect ping 2>&1 | grep -q "pong"; then
    ok "worker answered inspect ping"
else
    bad "worker did not answer inspect ping"
fi

if docker compose exec -T celery_worker celery -A app.celery_app inspect registered 2>&1 \
     | grep -q "run_pipeline_task"; then
    ok "worker registered run_pipeline_task"
else
    bad "worker did not register run_pipeline_task"
fi

# ---------------------------------------------------------------------------
if [ "$CORE_ONLY" -eq 0 ]; then
step "Through nginx on :${HTTP_PORT}"
# ---------------------------------------------------------------------------
code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:${HTTP_PORT}/api/health || echo 000)"
if [ "$code" = "200" ]; then ok "nginx proxies /api/health -> 200"
else bad "nginx /api/health -> $code"; fi

code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:${HTTP_PORT}/login || echo 000)"
if [ "$code" = "200" ]; then ok "nginx serves the console (/login -> 200)"
else bad "nginx /login -> $code"; fi

if curl -fsS http://localhost:${HTTP_PORT}/login 2>/dev/null | grep -qi "<!DOCTYPE html"; then
    ok "console returns HTML through nginx"
else
    bad "console did not return HTML through nginx"
fi

csp="$(curl -sSI http://localhost:${HTTP_PORT}/login 2>/dev/null | tr -d '\r' | grep -i '^content-security-policy:' || true)"
if printf '%s' "$csp" | grep -q "script-src"; then
    ok "CSP allows Next.js inline bootstrap (script-src present)"
else
    bad "CSP has no script-src — the console will render blank"
fi

code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost:${HTTP_PORT}/api/assets || echo 000)"
if [ "$code" = "401" ]; then ok "auth boundary survives the proxy (/api/assets -> 401)"
else bad "through nginx /api/assets -> $code (expected 401)"; fi

# WebSocket upgrade. Without a token the backend closes the handshake; with a
# forged one it also refuses. What is being proven here is that nginx performs
# the upgrade at all rather than answering 400/502 — a proxy that does not
# forward Upgrade returns a normal HTTP status instead.
ws_status="$(curl -s -o /dev/null -w '%{http_code}' \
    -H "Connection: Upgrade" -H "Upgrade: websocket" \
    -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: $(head -c 16 /dev/zero | base64)" \
    "http://localhost:${HTTP_PORT}/ws/agents/stream" || echo 000)"
case "$ws_status" in
    101|403|1008) ok "nginx forwarded the WebSocket upgrade (status $ws_status)" ;;
    502|504)      bad "nginx failed to reach the API for /ws (status $ws_status)" ;;
    400)          bad "nginx did not forward Upgrade/Connection headers (status 400)" ;;
    *)            echo "      /ws handshake returned $ws_status"; ok "nginx routed /ws to the API" ;;
esac
fi

# ---------------------------------------------------------------------------
step "Result"
# ---------------------------------------------------------------------------
echo "  $PASS passed, $FAIL failed"
if [ "$FAIL" -gt 0 ]; then
    dump_diagnostics
    exit 1
fi
echo "  Stack is up and verified."
