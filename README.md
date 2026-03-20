# VisionAudioForge — Elite Multimodal AI Platform

A 28-module multimodal AI operating system for capture, processing, training, deployment, and monitoring of computer vision and audio ML models. Built with FastAPI, Next.js 14, PyTorch, and modern AI/ML tooling.

**Version:** 1.0.0 | **Modules:** 28 | **API Endpoints:** 100+

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | Python 3.11, FastAPI, Pydantic v2, Uvicorn, Celery |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, React 18, Zustand, React Query, Recharts, React Flow |
| **Database** | PostgreSQL 16 + pgvector, Redis 7 |
| **AI/ML** | PyTorch, OpenCV, Librosa, FAISS, HuggingFace Transformers, CLIP, Ultralytics YOLO, scikit-learn |
| **NLP/AI** | Anthropic Claude API, sentence-transformers |
| **Edge/Export** | ONNX, ONNX Runtime, TensorRT, TFLite, CoreML, OpenVINO |
| **gRPC** | grpcio, grpcio-tools, proto3 definitions |
| **Storage** | MinIO (S3-compatible), boto3 (S3 connector) |
| **Infra** | Docker Compose, NGINX reverse proxy, Celery workers |
| **Auth** | JWT / OAuth2, role-based access control, SSO, API keys |
| **Observability** | Prometheus metrics, structured JSON logging, audit trail, request tracing, SRE dashboard |
| **Scheduling** | croniter (cron-based pipeline scheduling) |
| **Testing** | pytest, pytest-asyncio, httpx, pytest-cov |

## Modules

| # | Module | Route | Description | Status |
|---|--------|-------|-------------|--------|
| 1 | Health | `/api/health` | Service health with dependency checks (DB, Redis, MinIO) | Active |
| 2 | Metrics | `/api/metrics` | Prometheus metrics endpoint | Active |
| 3 | Auth | `/api/auth/*` | JWT login, register, token refresh, SSO, API keys | Active |
| 4 | Vision | `/api/vision/*` | Image analysis, optical flow, detection, OCR, error analysis | Active |
| 5 | Audio | `/api/audio/*` | Spectral analysis, augmentation pipeline, classification | Active |
| 6 | Transform | `/api/transform/*` | Audio transforms (denoise, EQ, pitch) and video transforms (super-res, style) | Active |
| 7 | Transfer | `/api/transfer/*` | Transfer learning with pre-trained models | Active |
| 8 | Experiments | `/api/experiments` | Experiment tracking with epoch metrics and comparison | Active |
| 9 | Registry | `/api/registry/*` | Model registry with versioning, lifecycle, rollback | Active |
| 10 | Search | `/api/search/*` | Cross-modal FAISS search with CLIP embeddings | Active |
| 11 | Pipeline | `/api/pipeline/*` | Visual pipeline builder with 20 node types, scheduling | Active |
| 12 | Alerts | `/api/alerts/*` | Alert rules and notification management | Active |
| 13 | Agents | `/api/agents/*` | AI copilot with Claude, agent memory, skill packs | Active |
| 14 | Assets | `/api/assets/*` | Media asset management with MinIO storage | Active |
| 15 | Datasets | `/api/datasets` | Dataset CRUD, upload, split, stats, export, versioning | Active |
| 16 | Safety | `/api/safety/*` | Content safety scanning | Active |
| 17 | Workspaces | `/api/workspaces` | Multi-tenant workspace management | Active |
| 18 | Capture | `/api/capture/*` | Live capture session management | Active |
| 19 | Evaluation | `/api/evaluation/*` | Benchmarks, tournaments, threshold analysis, scorecards | Active |
| 20 | Validation | `/api/validate/*` | Data drift detection, schema validation, explainability | Active |
| 21 | Investigation | `/api/investigate/*` | Case management, evidence linking, timeline queries | Active |
| 22 | Annotations | `/api/annotations/*` | CRUD, COCO/YOLO/VOC export/import, stats | Active |
| 23 | Governance | `/governance/*` | API keys, SSO, permissions, billing, feature flags | Active |
| 24 | Observability | `/api/observability/*` | SRE dashboard, SLA compliance, alert fatigue analytics | Active |
| 25 | Runtime | `/api/runtime/*` | GPU scheduling, model routing, cost control, inference cache | Active |
| 26 | Integrations | `/api/integrations/*` | Slack, Teams, email, webhooks, storage connectors, event bus | Active |
| 27 | Knowledge Graph | `/api/knowledge-graph/*` | Entity nodes, edges, neighbor queries, scene extraction | Active |
| 28 | Semantic Memory | `/api/semantic-memory/*` | Store, recall, decay, promote memories with importance scoring | Active |
| 29 | Command Center | `/api/command-center/*` | Multi-stream dashboard, layouts, operator shifts | Active |
| 30 | Simulation Lab | `/api/simulation/*` | Scenario generation, simulation execution, performance reports | Active |
| 31 | ReviewOps | `/api/reviewops/*` | Review task management, assignments, verdict workflow | Active |
| 32 | Edge Export | `/api/edge/*` | ONNX/TensorRT/TFLite/CoreML export with optimization | Active |
| 33 | Fleet Manager | `/api/fleet/*` | Edge device registration, heartbeat, fleet health | Active |
| 34 | Vertical Packs | `/api/verticals/*` | 7 industry packs (security, manufacturing, retail, healthcare, agriculture, logistics, media) | Active |
| 35 | Federated Learning | `/api/federated/*` | Federation management, participant join, training rounds | Active |
| 36 | Mobile Backend | `/api/mobile/*` | Mobile dashboard, push notifications, field notes | Active |
| 37 | Plugins | `/api/plugins/*` | Plugin marketplace, registration, enable/disable, execution | Active |
| 38 | Developer Tools | `/api/developer/*` | OpenAPI spec, gRPC proto, node templates, SDK info | Active |
| — | WebSocket | `/ws/live/stream/{id}` | Live video capture with per-frame analysis | Active |
| — | WebSocket | `/ws/agents/stream` | Streaming copilot chat | Active |

## Architecture

```
                          +-------------------+
                          |   NGINX (port 80) |
                          +--------+----------+
                                   |
                    +--------------+--------------+
                    |              |              |
              /     route    /api route     /ws route
                    |              |              |
           +-------v------+ +-----v------+ +-----v------+
           |  Frontend    | |  FastAPI   | |  WebSocket |
           |  Next.js 14  | |  Backend   | |  Handlers  |
           |  port 3000   | |  port 8000 | |  port 8000 |
           +--------------+ +-----+------+ +-----+------+
                                  |              |
                    +-------------+-------+------+
                    |             |        |
            +-------v---+ +------v--+ +---v--------+
            | PostgreSQL | |  Redis  | |   MinIO    |
            | + pgvector | | (cache  | | (S3 object |
            |            | |  + MQ)  | |  storage)  |
            +------------+ +---------+ +------------+
                                  |
                          +-------v-------+
                          | Celery Workers|
                          | (async tasks) |
                          +---------------+

API Layer (28 modules):
  Core:        health, metrics, auth, workspaces
  Vision:      vision, capture, annotations
  Audio:       audio, transform
  ML:          experiments, registry, transfer, evaluation, validation
  Data:        datasets, search, pipeline, assets, safety
  AI:          agents, knowledge-graph, semantic-memory, simulation
  Ops:         alerts, investigation, reviewops, observability, runtime
  Platform:    integrations, governance, edge, fleet, verticals
  Ecosystem:   federated, mobile, plugins, developer, command-center
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

### SDK Installation

**Python SDK:**

```bash
pip install visionaudioforge
```

```python
from visionaudioforge import VAFClient

client = VAFClient(base_url="http://localhost:8000")
result = client.vision.analyze("image.png")
```

**JavaScript SDK:**

```bash
npm install @visionaudioforge/sdk
```

```javascript
import { VAFClient } from '@visionaudioforge/sdk';

const client = new VAFClient({ baseUrl: 'http://localhost:8000' });
const result = await client.vision.analyze(file);
```

## API Overview

VisionAudioForge exposes 100+ endpoints across 28 modules. All endpoints are documented via:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **gRPC Proto**: `GET /api/developer/proto`
- **OpenAPI JSON**: `GET /api/developer/openapi`

See [docs/api-reference.md](docs/api-reference.md) for the full endpoint listing.

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

### Makefile

```bash
make dev              # Start all services (docker compose up)
make build            # Build containers
make stop             # Stop services
make clean            # Stop, remove volumes, clean caches
make logs             # Tail service logs
make migrate          # Run database migrations
make seed             # Seed database with sample data
make test             # Run all tests
make test-unit        # Unit tests only
make test-integration # Integration tests only
make test-coverage    # Tests with HTML coverage report
make lint             # Lint backend code
make format           # Format backend code
make sdk-python-test  # Test Python SDK
make sdk-js-build     # Build JavaScript SDK
```

## Testing

```bash
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-coverage     # Tests with HTML coverage report
```

### Test Categories

| Category | Command | Description |
|----------|---------|-------------|
| All | `make test` | Run full test suite |
| Unit | `make test-unit` | Fast isolated tests |
| Integration | `make test-integration` | API endpoint tests |
| E2E | `make test-e2e` | End-to-end flow tests |
| Coverage | `make test-coverage` | HTML coverage report |
| SDK Python | `make sdk-python-test` | Python SDK tests |
| SDK JS | `make sdk-js-build` | Build and test JS SDK |

## Deployment

### Production with Docker Compose

```bash
# Set production environment variables
cp .env.example .env
# Edit .env with production values (DB credentials, API keys, etc.)

# Build and start
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run migrations
docker compose exec api alembic upgrade head

# Seed initial data
docker compose exec api python -m app.scripts.seed
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@db/vaf` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `MINIO_ENDPOINT` | MinIO endpoint | `minio:9000` |
| `ANTHROPIC_API_KEY` | Claude API key for AI copilot | — |
| `SECRET_KEY` | JWT signing key | — |

## Contributing

1. Create a feature branch: `git checkout -b ai-feature/<slug>`
2. Follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
3. Add tests for new features
4. Ensure all tests pass before submitting
5. Update CHANGELOG.md with your changes

## License

Private / Proprietary
