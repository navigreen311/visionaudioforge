#!/bin/bash
# VisionAudioForge — Local Development Startup (No Docker)
# Usage: bash start-local.sh
# Idempotent: safe to run multiple times

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "=== VisionAudioForge Local Dev ==="

# 1. Check prerequisites
echo "[1/5] Checking prerequisites..."
command -v python >/dev/null 2>&1 || { echo "Python not found"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js not found"; exit 1; }
redis-cli ping >/dev/null 2>&1 || { echo "Redis not running. Start Redis first."; exit 1; }
"/c/Program Files/PostgreSQL/17/bin/pg_isready.exe" >/dev/null 2>&1 || { echo "PostgreSQL not running."; exit 1; }
echo "  All prerequisites OK"

# 2. Backend venv & deps
echo "[2/5] Setting up backend..."
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
    python -m venv venv
    ./venv/Scripts/python.exe -m pip install --upgrade pip -q
    ./venv/Scripts/python.exe -m pip install -r requirements-local.txt -q
fi

# 3. Ensure .env exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "  Creating backend .env from template..."
    cat > "$BACKEND_DIR/.env" << 'ENVEOF'
APP_NAME=VisionAudioForge
APP_ENV=development
DEBUG=true
SECRET_KEY=change-me-local
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=vaf
POSTGRES_PASSWORD=changeme
POSTGRES_DB=vaf
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=vaf-assets
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
TORCH_DEVICE=cpu
ANTHROPIC_API_KEY=YOUR_KEY_HERE
ENVEOF
fi

# 4. Run migrations (idempotent)
echo "[3/5] Running database migrations..."
cd "$BACKEND_DIR"
./venv/Scripts/python.exe -m alembic upgrade head 2>&1 | tail -1

# 5. Frontend deps
echo "[4/5] Setting up frontend..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    npm install
fi
if [ ! -f ".env.local" ]; then
    echo "NEXT_PUBLIC_API_URL=http://localhost:8001" > .env.local
fi

# 6. Start services
echo "[5/5] Starting services..."
cd "$BACKEND_DIR"
./venv/Scripts/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

cd "$FRONTEND_DIR"
npx next dev --port 3000 &
FRONTEND_PID=$!

echo ""
echo "=== VisionAudioForge is running ==="
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8001"
echo "  API Docs:  http://localhost:8001/docs"
echo "  PIDs: backend=$BACKEND_PID frontend=$FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
