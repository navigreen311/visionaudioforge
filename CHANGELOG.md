# Changelog

All notable changes to VisionAudioForge are documented in this file.

## [1.0.0] - 2026-03-20 (VisionAudioForge v1.0.0 — Complete Platform Release)

### Added

#### Knowledge Graph Engine
- Entity node and edge management with typed relations
- Neighbor traversal queries
- Scene extraction from natural language descriptions
- Graph-based entity linking for investigation and analysis

#### Semantic Memory System
- Memory store with importance scoring and category tagging
- Keyword-based recall with relevance ranking
- Time-based memory decay with configurable threshold and factor
- Memory promotion (importance boosting) for high-value entries

#### Command Center
- Multi-stream video dashboard with configurable layouts
- Stream management (add, list, status tracking)
- Operator shift scheduling and management
- Real-time operational dashboard with stream health

#### Simulation Lab
- Scenario generation with configurable parameters
- Simulation execution engine with performance metrics
- Detailed simulation reports (throughput, latency, error rate)

#### ReviewOps Workflow
- Review task creation and management
- Reviewer assignment workflow
- Verdict submission (approved, rejected, needs_changes)
- Task status tracking and completion checking

#### Edge Export & Fleet Manager
- Model export to ONNX, TensorRT, TFLite, CoreML, OpenVINO formats
- Export optimization and quantization options
- Edge device registration and management
- Device heartbeat monitoring with resource metrics
- Fleet-wide health summary dashboard

#### Python SDK & JavaScript SDK
- Python SDK: `pip install visionaudioforge`
- JavaScript SDK: `npm install @visionaudioforge/sdk`
- Full API coverage for all 28 modules
- Developer tools endpoint for SDK discovery

#### 7 Vertical Packs
- Security & Surveillance (intrusion detection, perimeter monitoring)
- Manufacturing QA (defect detection, assembly verification)
- Retail Analytics (foot traffic, heatmaps, queue detection)
- Healthcare Imaging (DICOM, pathology, radiology)
- Agriculture (crop health, NDVI, pest detection)
- Logistics & Warehouse (barcode, inventory, route optimization)
- Media & Entertainment (content moderation, highlights, auto-tagging)

#### Federated Learning
- Federation creation with configurable aggregation strategies
- Participant join workflow with data size reporting
- Training round management
- FedAvg aggregation support

#### Mobile Backend
- Mobile-optimized dashboard endpoint
- Push notification registration (iOS, Android, Web)
- Field note creation with location and attachments
- Mobile-friendly API responses

#### Plugin Marketplace
- Plugin registration with capability declaration
- Enable/disable lifecycle management
- Plugin execution engine
- Featured marketplace listings

#### gRPC API
- Proto3 service definitions for Vision, Audio, ModelRegistry, Pipeline, Search
- Proto file download endpoint
- grpcio and grpcio-tools integration

#### Developer Tools
- Full OpenAPI specification endpoint
- gRPC proto file access
- Pipeline node template creation and management
- SDK discovery and documentation links
- Developer health check endpoint

#### Integration & Infrastructure
- All 28 route modules registered in router.py
- Version bump to 1.0.0
- ONNX, ONNX Runtime dependencies for edge export
- grpcio, grpcio-tools for gRPC stubs
- Comprehensive V3 E2E test suite (14 test functions)
- Updated API reference with all Phase 4 endpoints
- Complete README rewrite for v1.0

## [0.3.0] - 2026-03-20 (Phase 3 — Advanced Platform Features)

### Added

#### WS01 — Evaluation Lab
- Benchmark creation and execution with multi-model comparison
- Round-robin tournament system for model ranking
- Threshold analysis (precision/recall/F1 across decision boundaries)
- Model scorecards with strengths/weaknesses summary

#### WS02 — Validation & Drift Detection
- Data drift detection (KL divergence, KS test, PSI)
- Schema validation for dataset columns
- Prediction explainability (feature importance, SHAP-style)
- Input constraint validation with configurable rules

#### WS03 — Investigation Workspace
- Case management with create/list/get/export
- Evidence linking (asset attachment to cases)
- Investigator notes with timestamped entries
- Timeline query with time-range and event-type filtering
- Full case export as structured JSON

#### WS04 — Capture Enhancements
- Live capture session management endpoints
- Frame-level analysis during capture
- Session metadata and replay support

#### WS05 — Advanced Vision
- Enhanced error analysis with confusion matrix
- Screen-analyze endpoint for desktop captures
- Annotated visualization with base64 output

#### WS06 — Advanced Audio
- Audio classification pipeline
- Enhanced spectral analysis with configurable feature extraction
- Audio augmentation chain (noise, pitch, time-stretch, filtering)

#### WS07 — Transform Pipeline
- Audio transform chain: denoise, silence removal, pitch shift, time stretch, EQ presets
- Video transforms: background removal, super resolution, style transfer, auto crop, thumbnails
- Composable transform runner for chained operations

#### WS08 — Dataset Versioning
- Dataset versioning with immutable snapshots
- Enhanced split with stratification support
- Statistics computation and JSON export

#### WS09 — Pipeline Scheduling
- Pipeline scheduling with cron expressions (croniter)
- Pipeline validation with node-type registry
- Run management with status tracking

#### WS10 — Alert System
- Alert rule creation with condition expressions
- Severity levels (info, warning, critical)
- Alert listing and acknowledgment

#### WS11 — Agent Memory
- Agent memory with importance scoring
- Memory decay mechanism
- Skill packs for specialized agent behavior

#### WS12 — Asset Management
- Media asset CRUD with MinIO storage
- Asset metadata and tagging
- Workspace-scoped asset listing

#### WS13 — Workspace Management
- Multi-tenant workspace CRUD
- Workspace-scoped resources across all modules

#### WS14 — Safety Scanning
- Content safety scanning endpoint
- Configurable safety policy rules

#### WS15 — Search Enhancements
- Cross-modal FAISS search with CLIP embeddings
- Search index statistics
- Similarity-based asset retrieval

#### WS16 — Metrics & Observability
- Prometheus metrics endpoint
- Request ID middleware for correlation
- Timing middleware for latency tracking
- Audit middleware for compliance logging
- Structured JSON logging

#### WS17 — Transfer Learning
- Transfer learning job creation
- Pre-trained model fine-tuning support

#### WS18 — Model Registry Enhancements
- Model lifecycle management (draft, active, archived, deprecated)
- Model comparison and rollback
- Version tracking

#### WS19 — Experiment Tracking Enhancements
- Enhanced epoch tracking with train_loss, val_loss, accuracy
- Training curve generation
- Experiment comparison across metrics

#### WS20 — Consolidation & Testing
- Route verification: all 22 route files registered in router
- Comprehensive E2E integration tests (10 test functions covering all subsystems)
- Health check for all endpoints (verify no 404s)
- Requirements update: croniter, scikit-learn, boto3
- CHANGELOG, README, API reference consolidation

## [0.2.0] - 2026-03-20 (Phase 2 — Full Feature Build)

### Added

#### Infrastructure & Observability (WS01, WS04)
- Docker Compose with 7 services (API, Frontend, DB, Redis, MinIO, NGINX, Celery)
- NGINX reverse proxy, multi-stage Dockerfiles
- Health check with dependency status (DB, Redis, MinIO)
- Prometheus metrics, request ID / timing / audit middleware
- Structured JSON logging with correlation IDs

#### Database & Auth (WS02, WS03)
- SQLAlchemy models: User, Workspace, Model, Experiment, Dataset, Asset, Pipeline, Alert, Embedding, Event, AuditLog, Agent, AgentMemory
- Alembic migration infrastructure with UUID primary keys
- JWT authentication (login, register, refresh, /me)
- Role-based access control middleware

#### Vision (WS05, WS06, WS07)
- Image analysis and screen-analyze endpoints
- Optical flow (Lucas-Kanade / Farneback) and frame differencing
- Object detection (YOLO), OCR text extraction
- Error analysis with confusion matrix and quality reports
- Annotated visualization with base64-encoded output

#### Audio (WS08, WS09, WS17)
- Spectral analysis service
- Audio augmentation pipeline (noise injection, pitch shift, time stretch, filtering)
- Audio transforms: denoise, silence removal, pitch shift, time stretch, loudness normalization, EQ presets
- Speech enhance chain and composable transform runner

#### Video Transforms (WS18)
- Background removal, super resolution, style transfer, auto crop, thumbnail generation
- Before/after slider component

#### Capture & Streaming (WS10)
- WebSocket live capture (`/ws/live/stream/{session_id}`)
- Per-frame motion detection, connection manager with channel routing

#### Model Registry & Experiments (WS11, WS12)
- Model registry CRUD with versioning and lifecycle (draft, active, archived, deprecated)
- Model comparison and rollback endpoints
- Experiment CRUD with epoch tracking (train_loss, val_loss, accuracy)
- Training curves, metrics recording, transfer learning service

#### Dataset Management (WS13)
- Dataset CRUD with workspace scoping and versioning
- File upload with MinIO storage, train/val/test split with stratification
- Statistics computation and export (JSON)

#### Search (WS14)
- Cross-modal FAISS search with CLIP embeddings
- Index management and search stats

#### Pipeline Builder (WS15)
- Visual pipeline builder with 20 node types
- Pipeline CRUD, run management, React Flow editor integration

#### Copilot Agent (WS16)
- Agentic media copilot with Claude API
- WebSocket streaming (`/ws/agents/stream`)
- Agent memory with importance scoring, skill packs

#### Frontend (WS19)
- Next.js 14 with 16 dashboard pages
- Sidebar navigation, Zustand auth store, React Query provider
- Train page (Models, Experiments, Datasets tabs)
- Transform page (Audio and Video tabs)
- Dataset management UI (upload, stats, split)

#### Testing & CI (WS20)
- Integration tests: vision pipeline, audio pipeline, model lifecycle, search, auth flow
- Test utilities with synthetic image/audio generators
- pytest with markers (unit, integration, e2e, slow), 50% coverage threshold
- GitHub Actions CI with PostgreSQL and Redis services

#### Integration Fixes (WS20 — Final)
- Dependency cleanup: added missing packages (ultralytics, pydub, sentence-transformers, pytest-cov)
- Frontend: added recharts for charting
- Complete API reference documentation
- Makefile consolidation with all development targets
- README with full module listing and setup instructions

## [0.1.0] - 2026-03-20 (Phase 1 — Scaffold)

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
