#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$PROJECT_DIR"

echo "=========================================="
echo "  VAF Production Deployment"
echo "=========================================="

# 1. Validate environment
if [ ! -f .env ]; then
    echo "ERROR: .env file not found. Copy .env.example and configure it."
    exit 1
fi

echo ""
echo "[1/5] Building production images..."
docker compose -f "$COMPOSE_FILE" build --no-cache

echo ""
echo "[2/5] Starting database services..."
docker compose -f "$COMPOSE_FILE" up -d db redis

echo "Waiting for database to be ready..."
timeout=60
elapsed=0
until docker compose -f "$COMPOSE_FILE" exec -T db pg_isready -U vaf > /dev/null 2>&1; do
    sleep 2
    elapsed=$((elapsed + 2))
    if [ "$elapsed" -ge "$timeout" ]; then
        echo "ERROR: Database failed to start within ${timeout}s"
        exit 1
    fi
done
echo "Database is ready."

echo ""
echo "[3/5] Running database migrations..."
docker compose -f "$COMPOSE_FILE" run --rm api alembic upgrade head || echo "WARN: No migrations found or alembic not configured. Skipping."

echo ""
echo "[4/5] Starting all services..."
docker compose -f "$COMPOSE_FILE" up -d

echo ""
echo "[5/5] Waiting for health checks..."
services=("api" "frontend" "db" "redis" "minio" "nginx")
timeout=120
for svc in "${services[@]}"; do
    elapsed=0
    echo -n "  Waiting for $svc..."
    until [ "$(docker compose -f "$COMPOSE_FILE" ps "$svc" --format json 2>/dev/null | grep -o '"Health":"[^"]*"' | head -1)" = '"Health":"healthy"' ]; do
        sleep 3
        elapsed=$((elapsed + 3))
        if [ "$elapsed" -ge "$timeout" ]; then
            echo " TIMEOUT (${timeout}s)"
            break
        fi
        echo -n "."
    done
    if [ "$elapsed" -lt "$timeout" ]; then
        echo " OK"
    fi
done

echo ""
echo "=========================================="
echo "  Deployment Status"
echo "=========================================="
docker compose -f "$COMPOSE_FILE" ps

echo ""
echo "Services:"
echo "  Frontend:  http://localhost:3000"
echo "  API:       http://localhost:8000"
echo "  Nginx:     http://localhost:80"
echo "  MinIO API: http://localhost:9000"
echo ""
echo "Deployment complete."
