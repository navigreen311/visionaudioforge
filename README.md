# VisionAudioForge

AI-powered vision and audio analysis platform for capture, processing, training, and deployment of computer vision and audio ML models. Built with FastAPI, Next.js 14, PyTorch, and modern AI/ML tooling.

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11, FastAPI, Pydantic v2, Uvicorn, Celery |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, React 18, Zustand, React Query |
| **Database** | PostgreSQL 16 + pgvector, Redis 7 |
| **AI/ML** | PyTorch, OpenCV, Librosa, FAISS, HuggingFace Transformers, CLIP, Ultralytics |
| **Storage** | MinIO (S3-compatible object storage) |
| **Infra** | Docker Compose, NGINX reverse proxy |
| **Auth** | JWT / OAuth2, role-based access control |
| **Observability** | Prometheus metrics, structured JSON logging, audit trail |

## Modules

| Module | Route | Description | Status |
|--------|-------|-------------|--------|
| Health | `/api/health` | Service health with dependency checks (DB, Redis, MinIO) | Active |
| Metrics | `/api/metrics` | Prometheus metrics endpoint | Active |
| Auth | `/api/auth/*` | JWT login, register, token refresh, user profile | Active |
| Vision | `/api/vision/*` | Image analysis, optical flow, detection, OCR, error analysis | Enhanced |
| Audio | `/api/audio/*` | Spectral analysis, audio augmentation pipeline | Enhanced |
| Transform | `/api/transform/*` | Audio transforms (denoise, EQ, pitch) and video transforms (super-res, style) | Active |
| Transfer | `/api/transfer/*` | Transfer learning with pre-trained models | Active |
| Experiments | `/api/experiments` | Experiment tracking with epoch metrics and comparison | Enhanced |
| Registry | `/api/registry/*` | Model registry with versioning, lifecycle, rollback | Enhanced |
| Search | `/api/search/*` | Cross-modal FAISS search with CLIP embeddings | Active |
| Pipeline | `/api/pipeline/*` | Visual pipeline builder with 20 node types | Active |
| Alerts | `/api/alerts/*` | Alert rules and notification management | Active |
| Agents | `/api/agents/*` | AI copilot with Claude, agent memory, skill packs | Active |
| Assets | `/api/assets/*` | Media asset management with MinIO storage | Active |
| Datasets | `/api/datasets` | Dataset CRUD, upload, split, stats, export, versioning | Enhanced |
| Safety | `/api/safety/*` | Content safety scanning | Active |
| Workspaces | `/api/workspaces` | Multi-tenant workspace management | Active |
| WebSocket | `/ws/live/stream/{id}` | Live video capture with per-frame analysis | Active |
| WebSocket | `/ws/agents/stream` | Streaming copilot chat | Active |

## Architecture

```
nginx (port 80) -> /     -> frontend:3000
                -> /api  -> api:8000
                -> /ws   -> api:8000 (WebSocket)

api -> PostgreSQL (pgvector)
    -> Redis (cache + Celery broker)
    -> MinIO (object storage)
    -> Celery workers (async tasks)
```

## Quick Start

```bash
# Clone and configure
git clone <repo-url>
cd visionaudioforge
cp .env.example .env

# Start all services
docker compose up --build

# Access
# Frontend:  http://localhost:3000
# API:       http://localhost:8000
# API Docs:  http://localhost:8000/docs
# MinIO:     http://localhost:9001
```

Or use the Makefile:

```bash
make dev       # Start all services
make build     # Build containers
make stop      # Stop services
make clean     # Stop and remove volumes
make logs      # Tail service logs
```

## Development Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Run locally (needs DB, Redis, MinIO running)
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev    # http://localhost:3000
```

## API Documentation

Interactive API docs are available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

See also: [docs/api-reference.md](docs/api-reference.md)

## Testing

```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-coverage     # Tests with HTML coverage report
make lint              # Lint backend code
make format            # Format backend code
```

## Contributing

1. Create a feature branch: `git checkout -b ai-feature/<slug>`
2. Follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
3. Add tests for new features
4. Ensure all tests pass before submitting
5. Update CHANGELOG.md with your changes

## License

Private / Proprietary
