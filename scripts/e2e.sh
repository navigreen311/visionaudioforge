#!/usr/bin/env bash
# Run the browser end-to-end suite against a real stack.
#
# The console's job is to talk to the backend through nginx. A Playwright
# `webServer` that starts only Next would test the console against nothing, so
# this brings the whole stack up first and points Playwright at the proxy.
#
# Reuses scripts/smoke-stack.sh for bring-up, so "the stack is healthy" is
# asserted by the same code the compose-smoke CI job uses -- and an e2e failure
# can never be a stack that was not ready.
#
# Usage:
#   scripts/e2e.sh                  # up, test, leave running
#   scripts/e2e.sh --down           # up, test, tear down (CI default)
#   scripts/e2e.sh -- --grep auth   # everything after -- goes to Playwright
#
# Ports default to 8080/3001 rather than 80/3000: a developer machine usually
# has something on those already, and a port clash looks exactly like a broken
# console.
set -euo pipefail

cd "$(dirname "$0")/.."

export HTTP_PORT="${HTTP_PORT:-8080}"
export FRONTEND_PORT="${FRONTEND_PORT:-3001}"
export E2E_BASE_URL="${E2E_BASE_URL:-http://localhost:${HTTP_PORT}}"

TEARDOWN=0
PW_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --down) TEARDOWN=1 ;;
        --) shift; PW_ARGS=("$@"); break ;;
        *) PW_ARGS+=("$1") ;;
    esac
    shift
done

cleanup() {
    if [[ "$TEARDOWN" == "1" ]]; then
        echo "==> tearing the stack down"
        docker compose down -v --remove-orphans || true
    fi
}
trap cleanup EXIT

echo "==> bringing the stack up and asserting it is healthy"
scripts/smoke-stack.sh

echo "==> installing the browser if it is missing"
( cd frontend && npx --yes playwright install --with-deps chromium >/dev/null 2>&1 \
    || npx --yes playwright install chromium )

echo "==> running the e2e suite against ${E2E_BASE_URL}"
cd frontend
npx playwright test "${PW_ARGS[@]}"
