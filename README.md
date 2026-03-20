# VisionAudioForge

AI-powered vision and audio analysis platform for capture, processing, training, and deployment of computer vision and audio ML models. Built with FastAPI, Next.js 14, PyTorch, and modern AI/ML tooling.

**Version:** 0.3.0 | **Modules:** 24 | **API Endpoints:** 70+

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11, FastAPI, Pydantic v2, Uvicorn, Celery |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, React 18, Zustand, React Query, Recharts, React Flow |
| **Database** | PostgreSQL 16 + pgvector, Redis 7 |
| **AI/ML** | PyTorch, OpenCV, Librosa, FAISS, HuggingFace Transformers, CLIP, Ultralytics YOLO, scikit-learn |
| **NLP/AI** | Anthropic Claude API, sentence-transformers |
| **Storage** | MinIO (S3-compatible), boto3 (S3 connector) |
| **Infra** | Docker Compose, NGINX reverse proxy, Celery workers |
| **Auth** | JWT / OAuth2, role-based access control |
| **Observability** | Prometheus metrics, structured JSON logging, audit trail, request tracing |
| **Scheduling** | croniter (cron-based pipeline scheduling) |
| **Testing** | pytest, pytest-asyncio, httpx, pytest-cov |

## Modules

| Module | Route | Description | Phase |
|--------|-------|-------------|-------|
| Health | `/api/health` | Service health with dependency checks (DB, Redis, MinIO) | V1 |
| Metrics | `/api/metrics` | Prometheus metrics endpoint | V1 |
| Auth | `/api/auth/*` | JWT login, register, token refresh, user profile | V1 |
| Vision | `/api/vision/*` | Image analysis, optical flow, detection, OCR, error analysis | V2 |
| Audio | `/api/audio/*` | Spectral analysis, augmentation pipeline, classification | V2 |
| Transform | `/api/transform/*` | Audio transforms (denoise, EQ, pitch) and video transforms (super-res, style) | V2 |
| Transfer | `/api/transfer/*` | Transfer learning with pre-trained models | V2 |
| Experiments | `/api/experiments` | Experiment tracking with epoch metrics and comparison | V2 |
| Registry | `/api/registry/*` | Model registry with versioning, lifecycle, rollback | V2 |
| Search | `/api/search/*` | Cross-modal FAISS search with CLIP embeddings | V2 |
| Pipeline | `/api/pipeline/*` | Visual pipeline builder with 20 node types, scheduling | V2 |
| Alerts | `/api/alerts/*` | Alert rules and notification management | V2 |
| Agents | `/api/agents/*` | AI copilot with Claude, agent memory, skill packs | V2 |
| Assets | `/api/assets/*` | Media asset management with MinIO storage | V2 |
| Datasets | `/api/datasets` | Dataset CRUD, upload, split, stats, export, versioning | V2 |
| Safety | `/api/safety/*` | Content safety scanning | V2 |
| Workspaces | `/api/workspaces` | Multi-tenant workspace management | V2 |
| Capture | `/api/capture/*` | Live capture session management | V2 |
| Evaluation | `/api/evaluation/*` | Benchmarks, tournaments, threshold analysis, scorecards | V3 |
| Validation | `/api/validate/*` | Data drift detection, schema validation, explainability | V3 |
| Investigation | `/api/investigate/*` | Case management, evidence linking, timeline queries | V3 |
| WebSocket | `/ws/live/stream/{id}` | Live video capture with per-frame analysis | V2 |
| WebSocket | `/ws/agents/stream` | Streaming copilot chat | V2 |

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

### Docker (recommended)

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

### Makefile

```bash
make dev       # Start all services (docker compose up)
make build     # Build containers
make stop      # Stop services
make clean     # Stop, remove volumes, clean caches
make logs      # Tail service logs
make migrate   # Run database migrations
make seed      # Seed database with sample data
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

### Test Categories

| Category | Command | Description |
|----------|---------|-------------|
| All | `make test` | Run full test suite |
| Unit | `make test-unit` | Fast isolated tests |
| Integration | `make test-integration` | API endpoint tests |
| Coverage | `make test-coverage` | HTML coverage report |

## Contributing

1. Create a feature branch: `git checkout -b ai-feature/<slug>`
2. Follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
3. Add tests for new features
4. Ensure all tests pass before submitting
5. Update CHANGELOG.md with your changes

## License

Private / Proprietary
