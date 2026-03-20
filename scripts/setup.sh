#!/usr/bin/env bash
set -euo pipefail

echo "=== VisionAudioForge Setup ==="

# Check dependencies
echo "Checking dependencies..."

command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required but not installed."; exit 1; }
command -v docker compose version >/dev/null 2>&1 || command -v docker-compose >/dev/null 2>&1 || { echo "ERROR: docker compose is required but not installed."; exit 1; }

echo "  docker: $(docker --version)"

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "  .env created. Please update with your actual secrets."
else
    echo "  .env already exists, skipping."
fi

# Build Docker images
echo "Building Docker images..."
docker compose build

echo ""
echo "=== Setup complete ==="
echo "Run 'docker compose up' or 'make dev' to start all services."
echo ""
echo "Services:"
echo "  Frontend:   http://localhost:3000"
echo "  API:        http://localhost:8000"
echo "  API Docs:   http://localhost:8000/docs"
echo "  MinIO:      http://localhost:9001"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:      localhost:6379"
