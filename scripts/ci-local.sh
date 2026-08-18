#!/usr/bin/env bash
#
# Reproduce the CI pipeline locally, idempotently.
#
#   scripts/ci-local.sh            # everything
#   scripts/ci-local.sh frontend   # lint + types + unit tests + build
#   scripts/ci-local.sh backend    # pytest against throwaway pg/redis
#
# The backend half needs Python 3.11 to match .github/workflows/test.yml —
# faiss-cpu==1.7.4 and onnx==1.15.0 publish no wheels for 3.12+, so a newer
# interpreter fails to install the pinned requirements at all.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VAF_VENV:-$REPO_ROOT/../vaf-venv311}"
PG_CONTAINER="vaf-ci-pg"
REDIS_CONTAINER="vaf-ci-redis"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }

python_311() {
  if command -v python3.11 >/dev/null 2>&1; then command -v python3.11; return; fi
  if command -v py >/dev/null 2>&1 && py -3.11 --version >/dev/null 2>&1; then
    echo "py -3.11"; return
  fi
  # uv ships standalone CPython builds and is the easiest way to get 3.11.
  if command -v uv >/dev/null 2>&1; then
    uv python install 3.11 >/dev/null
    uv python find 3.11
    return
  fi
  echo "ERROR: Python 3.11 not found. Install it, or install uv." >&2
  exit 1
}

run_frontend() {
  log "Frontend: install"
  cd "$REPO_ROOT/frontend"
  # npm ci is what CI runs; it needs the lockfile to be in sync.
  npm ci

  log "Frontend: lint"
  npm run lint

  log "Frontend: type check"
  npx tsc --noEmit

  log "Frontend: unit tests"
  npm test

  log "Frontend: build"
  npm run build
}

start_services() {
  if ! command -v docker >/dev/null 2>&1; then
    echo "docker not found — skipping service containers." >&2
    return
  fi
  log "Backend: starting postgres + redis"
  docker rm -f "$PG_CONTAINER" "$REDIS_CONTAINER" >/dev/null 2>&1 || true
  docker run -d --name "$PG_CONTAINER" \
    -e POSTGRES_DB=vaf_test -e POSTGRES_USER=vaf -e POSTGRES_PASSWORD=test \
    -p 5432:5432 postgres:16 >/dev/null
  docker run -d --name "$REDIS_CONTAINER" -p 6379:6379 redis:7 >/dev/null

  for _ in $(seq 1 30); do
    if docker exec "$PG_CONTAINER" pg_isready -U vaf >/dev/null 2>&1; then break; fi
    sleep 1
  done
}

run_backend() {
  if [ ! -x "$VENV_DIR/bin/python" ] && [ ! -x "$VENV_DIR/Scripts/python.exe" ]; then
    log "Backend: creating venv at $VENV_DIR"
    # shellcheck disable=SC2046
    $(python_311) -m venv "$VENV_DIR"
  fi

  local py="$VENV_DIR/bin/python"
  [ -x "$py" ] || py="$VENV_DIR/Scripts/python.exe"

  log "Backend: installing requirements"
  "$py" -m pip install --upgrade pip --quiet
  "$py" -m pip install -r "$REPO_ROOT/backend/requirements.txt" --quiet
  "$py" -m pip install pytest pytest-asyncio pytest-cov httpx --quiet

  start_services

  log "Backend: pytest"
  cd "$REPO_ROOT/backend"
  POSTGRES_HOST=localhost POSTGRES_PORT=5432 POSTGRES_USER=vaf \
  POSTGRES_PASSWORD=test POSTGRES_DB=vaf_test \
  REDIS_HOST=localhost REDIS_PORT=6379 REDIS_PASSWORD="" \
  JWT_SECRET_KEY=test-secret-key SECRET_KEY=test-secret-key APP_ENV=test \
    "$py" -m pytest tests/ -v
}

case "${1:-all}" in
  frontend) run_frontend ;;
  backend)  run_backend ;;
  all)      run_frontend; run_backend ;;
  *) echo "usage: $0 [all|frontend|backend]" >&2; exit 2 ;;
esac

log "Done."
