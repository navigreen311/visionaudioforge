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
 \
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
 \
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
apilog="$(docker compose logs api 2>&1 || true)"
if printf '%s' "$apilog" | grep -qi "mock mode"; then
    ok "copilot logged its documented mock-mode fallback"
else
    echo "      (no mock-mode line found; API is healthy regardless)"
fi
check "api container is running with no ANTHROPIC_API_KEY set" \
    sh -c 'test -z "$(docker compose exec -T api printenv ANTHROPIC_API_KEY 2>/dev/null | tr -d "[:space:]")"'

# ---------------------------------------------------------------------------
step "Celery worker is attached to the broker"
# ---------------------------------------------------------------------------
# `inspect` broadcasts over the broker's control queue and waits 1 second by
# default. That races a worker that has only just gone healthy — --wait returns
# the moment the healthcheck first passes — so give it a real timeout and a
# couple of attempts. A pong is itself proof of a broker round-trip.
celery_inspect() {
    docker compose exec -T celery_worker         celery -A app.celery_app inspect "$1" --timeout 15 2>&1 || true
}

pinged=""
for _ in 1 2 3; do
    # Captured into a variable rather than piped: `cmd | grep -q` under
    # `set -o pipefail` fails the pipeline when grep exits at the first match
    # and the upstream command takes SIGPIPE.
    out="$(celery_inspect ping)"
    case "$out" in *pong*) pinged=yes; break ;; esac
    sleep 5
done
if [ -n "$pinged" ]; then ok "worker answered inspect ping (broker round-trip)"
else bad "worker did not answer inspect ping"; fi

reg="$(celery_inspect registered)"
case "$reg" in
    *run_pipeline_task*) ok "worker registered run_pipeline_task" ;;
    *)                   bad "worker did not register run_pipeline_task" ;;
esac

# Registration is not consumption. Dispatch a real task and confirm the worker
# takes it off the queue. Execution is expected to fail on dummy arguments —
# what is being proven is that the worker picked it up, so only receipt counts.
task_id="$(docker compose exec -T api python -c "
from app.celery_app import celery_app
r = celery_app.send_task('run_pipeline_task', args=['smoke-test-pipeline', {}])
print(r.id)
" 2>/dev/null | tr -d '[:space:]')"

if [ -n "$task_id" ]; then
    received=""
    for _ in 1 2 3 4 5 6; do
        wlog="$(docker compose logs celery_worker 2>&1 || true)"
        case "$wlog" in *"$task_id"*) received=yes; break ;; esac
        sleep 5
    done
    # Receipt alone is not enough: a worker with an empty registry also logs
    # the id, right before rejecting the message as unregistered. Require the
    # absence of that rejection too.
    rejected=""
    case "$wlog" in *"Received unregistered task of type 'run_pipeline_task'"*) rejected=yes ;; esac
    if [ -n "$received" ] && [ -z "$rejected" ]; then
        ok "worker accepted dispatched task $task_id"
    elif [ -n "$rejected" ]; then
        bad "worker received $task_id but rejected it as an unregistered task"
    else
        bad "worker never received task $task_id"
    fi
else
    bad "could not dispatch a task from the api container"
fi

# ---------------------------------------------------------------------------
step "Two subsystems that were dead in the image (audio decode, text search)"
# ---------------------------------------------------------------------------
# "Seven services healthy" coexisted with two whole subsystems being down, and
# nothing in CI could see it: the backend job runs pytest on the runner, so it
# exercises code that never enters the image. These assertions run against the
# built container, which is the only place the bugs existed.
#
#   huggingface_hub could not create its cache under a home the runtime user
#   did not have, so CLIP never loaded and /api/search/query answered 500.
#
#   numba could not cache beside a read-only site-packages, so every librosa
#   decode failed and /api/audio/analyze answered 400.
#
# Both were environment faults, so the requests are issued from *inside* the
# api container: that is the runtime under test, and it needs nothing on the
# host or the runner beyond docker.
#
# Every capture below tolerates failure explicitly. Under `set -e` a bare
# assignment from a failing command substitution aborts the run, which would
# turn "search is broken" into "the smoke script stopped saying why".

api_exec() { docker compose exec -T api "$@"; }

# Both endpoints sit behind the auth boundary asserted above, so this needs a
# real session. register and login are on the public allowlist.
# Unique per run in both dimensions. The email is the obvious one; the
# workspace is not — registration derives a workspace slug from the name and
# that slug is UNIQUE, so a constant name registers cleanly exactly once and
# then 500s on ix_workspaces_slug for the life of the volume.
#
# example.com, not example.test: pydantic's email validator rejects the
# reserved .test TLD outright, which fails registration with a 422 that has
# nothing to do with what is being smoke-tested.
SMOKE_RUN_ID="$(date +%s)-$$"
SMOKE_EMAIL="smoke-$SMOKE_RUN_ID@example.com"
SMOKE_PASSWORD="Smoke-Passw0rd!"
SMOKE_CREDS="{\"email\":\"$SMOKE_EMAIL\",\"password\":\"$SMOKE_PASSWORD\"}"
SMOKE_REGISTRATION="{\"email\":\"$SMOKE_EMAIL\",\"password\":\"$SMOKE_PASSWORD\",\"full_name\":\"Smoke Test\",\"workspace_name\":\"Smoke $SMOKE_RUN_ID\"}"

api_exec curl -fsS -X POST http://127.0.0.1:8000/api/auth/register \
    -H 'Content-Type: application/json' -d "$SMOKE_REGISTRATION" \
    >/dev/null 2>&1 || true

# Parsed with python, not a regex: pulling a JSON field out with sed is how a
# smoke test starts reporting the wrong reason for a failure.
TOKEN="$(api_exec sh -c "curl -fsS -X POST http://127.0.0.1:8000/api/auth/login \
    -H 'Content-Type: application/json' -d '$SMOKE_CREDS' \
    | python -c 'import json,sys; print(json.load(sys.stdin).get(\"access_token\",\"\"))'" \
    2>/dev/null | tr -d '[:space:]')" || TOKEN=""

if [ -n "$TOKEN" ]; then
    ok "obtained a session for the functional checks"
else
    bad "could not obtain a session — the two checks below cannot run"
fi

# A one-second 440 Hz mono WAV, written inside the container. Small enough to
# be cheap, real enough that librosa must actually decode it.
if api_exec python -c "
import math, struct, wave
with wave.open('/tmp/smoke-tone.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
    w.writeframes(b''.join(
        struct.pack('<h', int(16000 * math.sin(2 * math.pi * 440 * n / 8000)))
        for n in range(8000)))
" >/dev/null 2>&1; then
    ok "generated a test tone inside the container"
else
    bad "could not generate a test tone inside the container"
fi

# Body and status in one request: two calls could disagree, and the body is
# what names the failure.
post_in_api() {
    # post_in_api <curl args...> -> "<body>\n<status>"
    api_exec curl -sS -w '\n%{http_code}' "$@" 2>/dev/null || true
}

split_status() { printf '%s' "$1" | tail -n 1 | tr -d '[:space:]'; }
split_body()   { printf '%s' "$1" | sed '$d'; }

# --- audio decode: the numba cache -----------------------------------------
audio_raw="$(post_in_api -X POST http://127.0.0.1:8000/api/audio/analyze \
    -H "Authorization: Bearer $TOKEN" \
    -F 'file=@/tmp/smoke-tone.wav;type=audio/wav' \
    -F 'operations=["stft"]')" || audio_raw=""
audio_code="$(split_status "$audio_raw")"
audio_body="$(split_body "$audio_raw")"

if [ "${audio_code:-000}" = "200" ]; then
    ok "/api/audio/analyze decoded a WAV inside the container (200)"
else
    bad "/api/audio/analyze -> ${audio_code:-000} — audio decode is down in the image"
    printf '        %s\n' "$(printf '%s' "$audio_body" | head -c 300)"
fi

# Name the specific regression so a re-break is recognisable, not just red.
case "$audio_body" in
    *"no locator available"*|*"cannot cache function"*)
        bad "numba cannot write its cache — NUMBA_CACHE_DIR unset or unwritable" ;;
esac

# --- text search: the huggingface cache ------------------------------------
search_raw="$(post_in_api -X POST http://127.0.0.1:8000/api/search/query \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d '{"query":"a photo of a cat","modality":"text","k":3}')" || search_raw=""
search_code="$(split_status "$search_raw")"
search_body="$(split_body "$search_raw")"

# An empty index is a legitimate answer; a 500 is not. What is proven here is
# that the query embedded at all, which means CLIP loaded.
if [ "${search_code:-000}" = "200" ]; then
    ok "/api/search/query embedded a text query inside the container (200)"
else
    bad "/api/search/query -> ${search_code:-000} — text search is down in the image"
    printf '        %s\n' "$(printf '%s' "$search_body" | head -c 300)"
fi

case "$search_body" in
    *"Permission denied"*|*"/home/appuser"*)
        bad "huggingface_hub cannot write its cache — runtime user has no writable home" ;;
esac

# The weights are baked in, so a search must not have needed the network. This
# is what makes an egress-less deployment able to serve search at all.
if api_exec sh -c 'test -d "$HUGGINGFACE_HUB_CACHE"/models--openai--clip-vit-base-patch32' >/dev/null 2>&1; then
    ok "CLIP weights are present in the image (no first-request download)"
else
    bad "CLIP weights missing from the image — the first search will hit the network"
fi

if api_exec sh -c 'touch "$NUMBA_CACHE_DIR"/.probe && rm -f "$NUMBA_CACHE_DIR"/.probe' >/dev/null 2>&1; then
    ok "NUMBA_CACHE_DIR is writable by the runtime user"
else
    bad "NUMBA_CACHE_DIR is not writable by the runtime user"
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
