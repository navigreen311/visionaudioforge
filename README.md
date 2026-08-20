# VisionAudioForge

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-Proprietary-red)
![Modules](https://img.shields.io/badge/modules-40-green)
![Endpoints](https://img.shields.io/badge/endpoints-587-orange)

VisionAudioForge is a 40-module enterprise multimodal AI platform for end-to-end capture, processing, training, deployment, and monitoring of computer vision and audio ML models. Built on FastAPI, Next.js 14, PyTorch, and modern AI/ML tooling, it delivers a complete production pipeline from data ingestion through edge deployment, with built-in SDKs, a visual pipeline builder, AI copilot, 7 industry vertical packs, and observability.

## Key Stats

Generated, not hand-maintained. Run `python scripts/readme-stats.py --write` to
refresh the badges and this table; CI runs `--check` and fails the build if they
have drifted. Endpoints come from walking the *mounted* FastAPI router, so a
decorator on a router nobody mounted is correctly not counted.

| Metric | Value | Counted from |
|--------|-------|--------------|
| **Modules** | 40 | rows in the module table below (57 routers are mounted — some modules mount more than one) |
| **Source Files** | 680 | `.py` / `.ts` / `.tsx` under `backend/app`, `frontend/src`, `sdk` |
| **API Endpoints** | 587 | method + path operations on the mounted router, across 526 distinct `/api` paths |
| **Vertical Packs** | 7 (Security, Industrial, Retail, Healthcare, Call Centre, Education, Media) | `backend/app/services/verticals/` |
| **SDKs** | 2 (Python, JavaScript) | `sdk/` |
| **Frontend Pages** | 28 dashboard views (30 routes including login and register) | `page.tsx` files under `frontend/src/app` |
| **Docker Services** | 7 (API, Frontend, DB, Redis, MinIO, NGINX, Celery) | `docker-compose.yml` |

## Feature Highlights

1. **Vision Pipeline** -- Image analysis, object detection (YOLO), optical flow, OCR, and error analysis with confusion matrices.
2. **Audio Pipeline** -- Spectral analysis, MFCC extraction, augmentation chains, and classification with Librosa and PyTorch.
3. **Cross-Modal Search** -- FAISS-powered similarity search with CLIP embeddings across images, audio, and text.
4. **Visual Pipeline Builder** -- Drag-and-drop pipeline editor with 26 node types, cron scheduling, and run management. Schedules are stored and listed; a scheduler process that fires them on their cron is not yet wired (that needs Celery Beat).
5. **AI Copilot** -- Claude-powered agentic assistant with streaming chat, persistent memory, and skill packs.
6. **Model Registry** -- Full lifecycle management (draft/active/archived/deprecated) with versioning, comparison, and rollback.
7. **Edge Export** -- One-click model export to ONNX, TensorRT, TFLite, CoreML, and OpenVINO with quantization options.
8. **7 Vertical Packs** -- Industry-specific solutions for security, manufacturing, retail, healthcare, agriculture, logistics, and media.
9. **Federated Learning** -- Privacy-preserving distributed training with FedAvg aggregation and participant management.
10. **Observability** -- Prometheus metric definitions, SRE dashboard, SLA reporting, alert fatigue analytics, and an audit trail written to `audit_logs`. Alert fatigue is computed from the alerts table. Request-level instrumentation is not yet wired, so the SRE dashboard and SLA report state which figures are unmeasured rather than filling them in — an SLA report will not claim compliance it cannot evidence.

## Architecture

```
                           +-----------------------+
                           |   NGINX (port 80)     |
                           +-----------+-----------+
                                       |
                    +------------------+------------------+
                    |                  |                  |
              /     route        /api route         /ws route
                    |                  |                  |
           +-------v--------+ +-------v--------+ +------v--------+
           |   Frontend     | |    FastAPI      | |   WebSocket   |
           |   Next.js 14   | |    Backend      | |   Handlers    |
           |   port 3000    | |    port 8000    | |   port 8000   |
           +----------------+ +-------+--------+ +------+--------+
                                      |                  |
                       +--------------+--------+---------+
                       |              |        |
               +-------v----+ +------v--+ +---v---------+
               | PostgreSQL | |  Redis  | |    MinIO     |
               | + pgvector | | (cache  | | (S3 object  |
               | + FAISS    | |  + MQ)  | |  storage)   |
               +------------+ +----+----+ +-------------+
                                   |
                           +-------v--------+
                           | Celery Workers  |
                           | (async tasks)   |
                           +----------------+

Module Groups:
  Core:       health, metrics, auth, workspaces, governance
  Vision:     vision, capture, annotations, command-center
  Audio:      audio, transform
  ML:         experiments, registry, transfer, evaluation, validation
  Data:       datasets, search, pipeline, assets, safety
  AI:         agents, knowledge-graph, semantic-memory, simulation
  Ops:        alerts, investigation, reviewops, observability, runtime
  Platform:   integrations, edge, fleet, verticals, federated
  Ecosystem:  mobile, plugins, developer
```

## Complete Module Table

| # | Module | Route Prefix | Description |
|---|--------|-------------|-------------|
| 1 | Health | `/api/health` | Service health with dependency checks (DB, Redis, MinIO) |
| 2 | Metrics | `/api/metrics` | Prometheus-format metrics endpoint |
| 3 | Auth | `/api/auth/*` | JWT login, register, token refresh, SSO, API keys |
| 4 | Vision | `/api/vision/*` | Image analysis, optical flow, detection, OCR, error analysis |
| 5 | Audio | `/api/audio/*` | Spectral analysis, augmentation pipeline, classification |
| 6 | Transform | `/api/transform/*` | Audio transforms (denoise, EQ, pitch) and video transforms (super-res, style) |
| 7 | Transfer | `/api/transfer/*` | Transfer learning with pre-trained models |
| 8 | Experiments | `/api/experiments` | Experiment tracking with epoch metrics and comparison |
| 9 | Registry | `/api/registry/*` | Model registry with versioning, lifecycle, rollback |
| 10 | Search | `/api/search/*` | Cross-modal FAISS search with CLIP embeddings |
| 11 | Pipeline | `/api/pipeline/*` | Visual pipeline builder with 26 node types, schedule storage |
| 12 | Alerts | `/api/alerts/*` | Alert rules and notification management |
| 13 | Agents | `/api/agents/*` | AI copilot with Claude, agent memory, skill packs |
| 14 | Assets | `/api/assets/*` | Media asset management with MinIO storage |
| 15 | Datasets | `/api/datasets` | Dataset CRUD, upload, split, stats, export, versioning |
| 16 | Safety | `/api/safety/*` | Content safety scanning |
| 17 | Workspaces | `/api/workspaces` | Multi-tenant workspace management |
| 18 | Capture | `/api/capture/*` | Live capture session management |
| 19 | Evaluation | `/api/evaluation/*` | Benchmarks, tournaments, threshold analysis, scorecards |
| 20 | Validation | `/api/validate/*` | Data drift detection, schema validation, explainability |
| 21 | Investigation | `/api/investigate/*` | Case management, evidence linking, timeline queries |
| 22 | Annotations | `/api/annotations/*` | CRUD, COCO/YOLO/VOC export/import, stats |
| 23 | Governance | `/governance/*` | API keys, SSO, permissions, billing, feature flags |
| 24 | Observability | `/api/observability/*` | SRE dashboard, SLA compliance, alert fatigue analytics |
| 25 | Runtime | `/api/runtime/*` | GPU scheduling, model routing, cost control, inference cache |
| 26 | Integrations | `/api/integrations/*` | Slack, Teams, email, webhooks, storage connectors |
| 27 | Knowledge Graph | `/api/knowledge-graph/*` | Entity nodes, edges, neighbor queries, scene extraction |
| 28 | Semantic Memory | `/api/semantic-memory/*` | Store, recall, decay, promote memories with importance scoring |
| -- | Command Center | `/api/command-center/*` | Multi-stream dashboard, layouts, operator shifts |
| -- | Simulation Lab | `/api/simulation/*` | Scenario generation, simulation execution, reports |
| -- | ReviewOps | `/api/reviewops/*` | Review task management, assignments, verdict workflow |
| -- | Edge Export | `/api/edge/*` | ONNX/TensorRT/TFLite/CoreML export with optimization |
| -- | Fleet Manager | `/api/fleet/*` | Edge device registration, heartbeat, fleet health |
| -- | Vertical Packs | `/api/verticals/*` | 7 industry packs (security, industrial, retail, healthcare, callcentre, education, media) |
| -- | Federated Learning | `/api/federated/*` | Federation management, participant join, training rounds |
| -- | Mobile Backend | `/api/mobile/*` | Mobile dashboard, push notifications, field notes |
| -- | Plugins | `/api/plugins/*` | Plugin marketplace, registration, enable/disable, execution |
| -- | Developer Tools | `/api/developer/*` | OpenAPI spec, gRPC proto, node templates, SDK info |
| -- | WebSocket | `/ws/live/stream/{id}` | Live video capture with per-frame analysis |
| -- | WebSocket | `/ws/agents/stream` | Streaming copilot chat |

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, React 18, Zustand, React Query, Recharts, React Flow |
| **Backend** | Python 3.11, FastAPI, Pydantic v2, Uvicorn, Celery |
| **Databases** | PostgreSQL 16 + pgvector, Redis 7 |
| **AI / ML** | PyTorch, OpenCV, Librosa, FAISS, HuggingFace Transformers, CLIP, Ultralytics YOLO, scikit-learn |
| **NLP / AI** | Anthropic Claude API, sentence-transformers |
| **Edge Export** | ONNX, ONNX Runtime, TensorRT, TFLite, CoreML, OpenVINO |
| **gRPC** | grpcio, grpcio-tools, proto3 definitions |
| **Storage** | MinIO (S3-compatible), boto3 |
| **Infrastructure** | Docker Compose, NGINX reverse proxy, Celery workers |
| **Auth** | JWT / OAuth2, role-based access control, SSO, API keys |
| **Observability** | Prometheus metric definitions, structured JSON logging, audit trail, request tracing |
| **Testing** | pytest, pytest-asyncio, httpx, pytest-cov |

## State and Persistence

Application state lives in PostgreSQL, and capture sessions in Redis. This
matters for anyone running more than one worker: state held in a process is
neither shared between workers nor survives a deploy, and a subsystem that
loses it usually reports "nothing here" rather than an error.

Everything below is backed by a table with an Alembic migration, scoped by
workspace, and covered by a test that writes through one connection and reads
back through a new one:

| Area | Tables |
|------|--------|
| Identity and access | `users`, `workspaces`, `api_keys`, `user_sessions`, `login_events`, `user_two_factor` |
| Evidence and integrity | `evidence_bundles`, `custody_events`, `asset_integrity`, `provenance_events` |
| Alerting and review | `alert_rules`, `alerts`, `review_tasks`, `reviews`, `review_shifts` |
| Knowledge | `graph_nodes`, `graph_edges`, `semantic_memories`, `agent_conversations`, `agent_messages` |
| Scheduling and cost | `pipeline_schedules`, `inference_cost_events`, `workspace_quotas`, `model_cost_rates` |
| Edge and fleet | `edge_devices`, `ota_updates`, `offline_packages`, `model_exports`, `edge_benchmarks` |
| Platform | `installed_vertical_packs`, `simulation_runs`, `field_notes`, `workspace_integrations`, `appearance_preferences` |

Two stores are deliberately still in memory, and say so in the code:

- the installer's loaded `VerticalPack` instances — live objects, not state;
  the fact of an install is a row in `installed_vertical_packs`
- the inference cache and loaded model handles — a cache is expected to be cold
  after a restart

## Quick Start

```bash
git clone <repo-url> && cd visionaudioforge
cp .env.example .env
docker compose up --build
# Open http://localhost:3000
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

## Development Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

## SDK Usage

### Python

```python
from visionaudioforge import VAFClient
client = VAFClient(base_url="http://localhost:8000")
result = client.vision.analyze("image.png")
```

### JavaScript

```javascript
import { VAFClient } from '@visionaudioforge/sdk';
const client = new VAFClient({ baseUrl: 'http://localhost:8000' });
const result = await client.vision.analyze(file);
```

## Testing

```bash
make test              # Run full test suite
make test-coverage     # Tests with HTML coverage report
```

| Category | Command | Description |
|----------|---------|-------------|
| All | `make test` | Run full test suite |
| Unit | `make test-unit` | Fast isolated tests |
| Integration | `make test-integration` | API endpoint tests |
| E2E | `make test-e2e` | End-to-end flow tests |
| Coverage | `make test-coverage` | HTML coverage report |
| SDK Python | `make sdk-python-test` | Python SDK tests |
| SDK JS | `make sdk-js-build` | Build and test JS SDK |

## API Documentation

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: `GET /api/developer/openapi`
- **gRPC Proto**: `GET /api/developer/proto`
- **Full Reference**: [docs/api-reference.md](docs/api-reference.md)

## Project Structure

```
visionaudioforge/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── api/             # Route handlers (38 route files)
│   │   ├── models/          # SQLAlchemy database models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (32 service modules)
│   │   ├── core/            # Config, security, dependencies
│   │   ├── middleware/       # Auth, timing, audit, request ID
│   │   ├── tasks/           # Celery async tasks
│   │   ├── grpc/            # Proto definitions and stubs
│   │   └── ws/              # WebSocket handlers
│   ├── tests/               # pytest test suites
│   └── alembic/             # Database migrations
├── frontend/                # Next.js 14 application
│   └── src/
│       ├── app/             # Pages (16 dashboard views)
│       ├── components/      # React components
│       ├── lib/             # API client, utilities
│       └── stores/          # Zustand state management
├── sdk/
│   ├── python/              # Python SDK package
│   └── javascript/          # JavaScript/TypeScript SDK
├── nginx/                   # NGINX reverse proxy config
├── docs/                    # Feature documentation (16 guides)
├── scripts/                 # Utility scripts
├── docker-compose.yml       # 7-service orchestration
├── Makefile                 # Development commands
└── CLAUDE.md                # AI assistant context
```

## Contributing

1. Create a feature branch: `git checkout -b ai-feature/<slug>`
2. Follow Conventional Commits: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
3. Add tests for new features
4. Ensure all tests pass: `make test`
5. Update `CHANGELOG.md` with your changes

## License

Proprietary. All rights reserved.
