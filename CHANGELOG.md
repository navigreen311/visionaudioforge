# Changelog

All notable changes to VisionAudioForge are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased] — Persistence long tail, SDK coverage, honest README

### Added
- **Persistence for the remaining in-memory subsystems.** Twenty files still
  held state in module-level dicts, so it was lost on restart and not shared
  between workers. Migrations 007–016 add tables for asset provenance, account
  security (sessions, login history, two-factor), settings, pipeline schedules,
  inference cost and quotas, agent conversations, installed vertical packs,
  simulation scenarios and runs, field notes, and model exports and benchmarks.
  Every converted subsystem is workspace-scoped and covered by a test that
  writes through one connection and reads back through a fresh one.
- **`app/services/observability/metrics_source.py`** — reads measured values out
  of the live Prometheus registry, and reports `observed=False` where nothing
  has been recorded rather than substituting a plausible number.
- **SDK test coverage.** Python: 39 tests (was 11), every client method driven
  against a mocked transport with its request path asserted, plus 401/403/404/
  422/429/500, unmapped statuses and non-JSON error bodies. JavaScript: 30
  tests (was 14) with paths and HTTP methods pinned.

### Fixed
- **The Python SDK targeted an API surface that does not exist.** It was written
  against `/api/v1/*`; only health, audio, stt, tts, speaker, sentiment,
  meeting, translate and vision live there. Auth, assets, datasets, models,
  search, pipelines, agents, alerts and transform all 404'd. Also: models now
  target `/api/registry`, training targets `/api/experiments`, and
  `search.similar` and `models.compare` send POST rather than GET.
- **The JavaScript SDK sent API keys as bearer tokens.** `Authorization: Bearer
  <api-key>` is rejected — the server only accepts keys on `X-API-Key`. Its
  `npm test` script also never ran, dying with a SyntaxError before executing
  any test.
- **Two-factor enrolment was global.** A single module-level boolean meant one
  account enabling 2FA reported it as enabled for every user; sessions and
  appearance preferences were shared the same way.
- **Inference quotas were not caps.** They reset on every deploy, and each
  worker counted its own usage, so a four-worker deployment allowed roughly
  four times the configured limit. `check_quota` now takes a row lock.
- **The knowledge-graph service layer was unimportable.** A duplicate
  `app/models/knowledge_graph.py` redefined `graph_nodes`/`graph_edges` with
  columns the database does not have, so importing it alongside the registered
  models raised "Table already defined". Removed; migration 010 adds the one
  column it contributed that `GraphService` actually writes.
- Unmapped HTTP statuses raised `VAFError` with `status_code=None`, so a caller
  could not tell a 502 from a proxy apart from a bad request.
- `get_pool_stats` raised on pool implementations that do not report statistics.

### Changed
- **Removed fabricated data from API responses.** A fresh install reported
  eight review tasks nobody created, a leaderboard of six reviewers who did not
  exist, a hand-written confusion matrix, five past model exports, four edge
  devices, three agent conversations, and two configured integrations. Unknown
  figures now report `null` or `supported: false` — an SLA report will not
  claim compliance it cannot evidence, and `auto-assign` no longer reports
  twelve assignments without making any.
- The knowledge graph returned a "Mock Node" for any id, three invented edges
  for any node, three search hits for any query, and a fixed two-hop path
  whether or not one existed. `/path` now runs a real breadth-first search and
  reports `found: false` when there is none.
- **README corrected against the code**: 563 endpoints across 492 paths (was
  "327+"), 40 modules (was 28), 830 source files (was "540+"), 28 dashboard
  pages (was 16), 26 pipeline node types (was 20), and the vertical pack names
  (manufacturing, agriculture and logistics were listed; the packs are
  industrial, call centre and education).

---

## [1.0.0] - 2026-03-20 — VisionAudioForge Complete Platform (Phase 4: 20 Workstreams)

### Added
- **Knowledge Graph Engine**: Entity node/edge management, typed relations, neighbor traversal, scene extraction from natural language
- **Semantic Memory System**: Importance-scored memory store, keyword recall, time-based decay, memory promotion
- **Command Center**: Multi-stream video dashboard, configurable layouts, operator shift scheduling, stream health monitoring
- **Simulation Lab**: Scenario generation with configurable parameters, simulation execution engine, performance reports (throughput, latency, error rate)
- **ReviewOps Workflow**: Review task creation, reviewer assignment, verdict submission (approved/rejected/needs_changes), status tracking
- **Edge Export**: Model export to ONNX, TensorRT, TFLite, CoreML, OpenVINO with quantization and optimization options
- **Fleet Manager**: Edge device registration, heartbeat monitoring with resource metrics, fleet-wide health dashboard
- **Python SDK** (`pip install visionaudioforge`): Full API coverage for all modules with typed client
- **JavaScript SDK** (`npm install @visionaudioforge/sdk`): TypeScript SDK with full API coverage
- **7 Vertical Packs**: Security/Surveillance, Manufacturing QA, Retail Analytics, Healthcare Imaging, Agriculture, Logistics/Warehouse, Media/Entertainment
- **Federated Learning**: Federation creation, participant join workflow, training round management, FedAvg aggregation
- **Mobile Backend**: Mobile-optimized dashboard, push notification registration (iOS/Android/Web), field notes with location
- **Plugin Marketplace**: Plugin registration with capability declaration, enable/disable lifecycle, plugin execution engine
- **gRPC API**: Proto3 service definitions for Vision, Audio, ModelRegistry, Pipeline, Search; proto file download endpoint
- **Developer Tools**: OpenAPI spec endpoint, gRPC proto access, pipeline node templates, SDK discovery and docs
- **Comprehensive V3 E2E test suite** with 14 test functions covering all Phase 4 subsystems

### Changed
- All 28+ route modules registered in unified `router.py`
- Version bumped to 1.0.0
- Dependencies updated: added ONNX, ONNX Runtime, grpcio, grpcio-tools
- Complete README rewrite and API reference update for v1.0.0

---

## [0.3.0] - 2026-03-20 — Advanced Platform Features (Phase 3: 20 Workstreams)

### Added
- **WS01 Evaluation Lab**: Benchmark creation/execution, round-robin tournament system, threshold analysis (precision/recall/F1), model scorecards
- **WS02 Validation & Drift Detection**: KL divergence, KS test, PSI drift detection; schema validation; prediction explainability; input constraint validation
- **WS03 Investigation Workspace**: Case management (create/list/get/export), evidence linking, investigator notes, timeline queries, full case export as JSON
- **WS04 Capture Enhancements**: Live capture session management, frame-level analysis, session metadata and replay
- **WS05 Advanced Vision**: Enhanced error analysis with confusion matrix, screen-analyze endpoint, annotated visualization with base64 output
- **WS06 Advanced Audio**: Audio classification pipeline, enhanced spectral analysis, augmentation chain (noise, pitch, time-stretch, filtering)
- **WS07 Transform Pipeline**: Audio transforms (denoise, silence removal, pitch shift, time stretch, EQ presets); video transforms (background removal, super resolution, style transfer, auto crop, thumbnails); composable transform runner
- **WS08 Dataset Versioning**: Immutable version snapshots, enhanced split with stratification, statistics computation, JSON export
- **WS09 Pipeline Scheduling**: Cron-based scheduling with croniter, pipeline validation with node-type registry, run management with status tracking
- **WS10 Alert System**: Alert rule creation with condition expressions, severity levels (info/warning/critical), alert acknowledgment
- **WS11 Agent Memory**: Importance-scored agent memory, memory decay mechanism, skill packs for specialized behavior
- **WS12 Asset Management**: Media asset CRUD with MinIO storage, asset metadata and tagging, workspace-scoped listing
- **WS13 Workspace Management**: Multi-tenant workspace CRUD, workspace-scoped resources across all modules
- **WS14 Safety Scanning**: Content safety scanning endpoint, configurable safety policy rules
- **WS15 Search Enhancements**: Cross-modal FAISS search with CLIP embeddings, search index statistics, similarity-based retrieval
- **WS16 Metrics & Observability**: Prometheus metrics endpoint, request ID middleware, timing middleware, audit middleware, structured JSON logging
- **WS17 Transfer Learning**: Transfer learning job creation, pre-trained model fine-tuning support
- **WS18 Model Registry Enhancements**: Lifecycle management (draft/active/archived/deprecated), model comparison, rollback, version tracking
- **WS19 Experiment Tracking Enhancements**: Enhanced epoch tracking (train_loss, val_loss, accuracy), training curve generation, experiment comparison
- **WS20 Consolidation & Testing**: Route verification for all 22 route files, comprehensive E2E integration tests (10 functions), requirements update (croniter, scikit-learn, boto3)

### Changed
- CHANGELOG, README, and API reference consolidated
- Health check updated to verify all endpoints return non-404

---

## [0.2.0] - 2026-03-20 — Full Feature Build (Phase 2: 20 Workstreams)

### Added
- **Infrastructure (WS01, WS04)**: Docker Compose with 7 services (API, Frontend, DB, Redis, MinIO, NGINX, Celery); NGINX reverse proxy; multi-stage Dockerfiles; Prometheus metrics; request ID / timing / audit middleware; structured JSON logging
- **Database & Auth (WS02, WS03)**: SQLAlchemy models (User, Workspace, Model, Experiment, Dataset, Asset, Pipeline, Alert, Embedding, Event, AuditLog, Agent, AgentMemory); Alembic migrations with UUID PKs; JWT auth (login, register, refresh, /me); role-based access control
- **Vision (WS05, WS06, WS07)**: Image analysis, optical flow (Lucas-Kanade/Farneback), frame differencing, YOLO object detection, OCR, error analysis with confusion matrix, annotated visualization
- **Audio (WS08, WS09, WS17)**: Spectral analysis, augmentation pipeline (noise injection, pitch shift, time stretch, filtering), audio transforms (denoise, silence removal, EQ presets), speech enhance chain
- **Video Transforms (WS18)**: Background removal, super resolution, style transfer, auto crop, thumbnail generation, before/after slider component
- **Capture & Streaming (WS10)**: WebSocket live capture (`/ws/live/stream/{id}`), per-frame motion detection, connection manager with channel routing
- **Model Registry & Experiments (WS11, WS12)**: Model CRUD with versioning and lifecycle, comparison and rollback; experiment CRUD with epoch tracking, training curves, transfer learning service
- **Dataset Management (WS13)**: Dataset CRUD with workspace scoping, MinIO file upload, train/val/test split with stratification, statistics and JSON export
- **Search (WS14)**: Cross-modal FAISS search with CLIP embeddings, index management and stats
- **Pipeline Builder (WS15)**: Visual pipeline builder with 20 node types, pipeline CRUD, run management, React Flow editor
- **Copilot Agent (WS16)**: Claude-powered agentic media copilot, WebSocket streaming (`/ws/agents/stream`), agent memory with importance scoring, skill packs
- **Frontend (WS19)**: Next.js 14 with 16 dashboard pages, sidebar navigation, Zustand auth store, React Query provider, Train page (Models/Experiments/Datasets), Transform page (Audio/Video), Dataset management UI
- **Testing & CI (WS20)**: Integration tests for vision, audio, model lifecycle, search, auth flow; synthetic image/audio test generators; pytest with markers (unit/integration/e2e/slow); 50% coverage threshold; GitHub Actions CI

### Changed
- Dependency cleanup: added ultralytics, pydub, sentence-transformers, pytest-cov, recharts
- Complete API reference documentation
- Makefile consolidated with all development targets

---

## [0.1.0] - 2026-03-20 — Platform Scaffold (Phase 1: 20 Workstreams)

### Added
- Initial project scaffold with full directory structure
- FastAPI backend with modular service architecture
- Next.js 14 frontend scaffold with TypeScript and Tailwind CSS
- Docker Compose configuration for all services
- Project configuration and CLAUDE.md
- Base database models and Alembic migration setup
- Core middleware stubs (CORS, request ID, timing, audit)
- Health check and metrics endpoints
- Authentication route stubs (login, register, /me)
- Vision, audio, and transform route stubs
- Test infrastructure with pytest and conftest fixtures
