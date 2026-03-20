# Changelog

## [0.2.0] - 2026-03-20

### Added

#### WS01 — Docker Infrastructure
- Docker Compose configuration with 7 services (API, Frontend, DB, Redis, MinIO, NGINX, Celery)
- NGINX reverse proxy configuration
- Multi-stage Dockerfiles for backend and frontend

#### WS02 — Database & Migrations
- SQLAlchemy models for all domain entities (User, Workspace, Model, Experiment, Dataset, Asset, Pipeline, Alert, Embedding, Event, AuditLog, Agent, AgentMemory)
- Alembic migration infrastructure with auto-generation support
- UUID primary keys with timestamp mixins

#### WS03 — Auth System
- JWT-based authentication with login, register, refresh endpoints
- Role-based access control middleware
- `GET /api/auth/me` endpoint

#### WS04 — Health & Observability
- Health check endpoint with dependency status (DB, Redis, MinIO)
- Prometheus metrics endpoint
- Request ID middleware for distributed tracing
- Timing middleware for request duration logging
- Audit middleware for request logging to database
- Structured logging with correlation IDs

#### WS05 — Vision Preprocessing
- Vision analyze and screen-analyze stub endpoints
- Image preprocessing utilities

#### WS06 — Vision Optical Flow
- Optical flow endpoint for motion analysis
- Frame diff endpoint for change detection

#### WS07 — Vision Detection & OCR
- Object detection endpoint with YOLO-based detector
- OCR endpoint with text extraction
- Error analysis endpoint with confusion matrix and quality reports
- Annotated visualization output with base64-encoded images

#### WS08 — Audio Spectral Analysis
- Audio analyze endpoint (stub)
- Spectral analysis service foundations

#### WS09 — Audio Augmentation
- Audio augment endpoint with configurable pipeline
- Augmentation presets (speech_robust, etc.)
- Support for noise injection, pitch shift, time stretch, and filtering
- Base64-encoded WAV output

#### WS10 — Capture Engine
- WebSocket live capture endpoint (`/ws/live/stream/{session_id}`)
- Per-frame analysis with motion detection
- Connection manager with channel-based routing

#### WS11 — Model Registry
- Model registry CRUD endpoints with versioning
- Model lifecycle management (draft, active, archived, deprecated)
- Model comparison endpoint

#### WS12 — Experiment Tracker
- Experiment CRUD with epoch tracking
- Training curves and metrics recording
- Transfer learning service
- ExperimentEpoch model with train_loss, val_loss, accuracy, val_accuracy

#### WS13 — Dataset Manager
- Dataset CRUD with workspace scoping
- File upload with MinIO storage
- Train/val/test split with stratification
- Dataset statistics computation
- Export endpoint (JSON format)
- Dataset versioning

#### WS14 — FAISS Search
- Cross-modal search with CLIP embeddings
- FAISS index management
- Search stats endpoint (`GET /api/search/stats`)

#### WS15 — Pipeline Builder
- Visual pipeline builder with 20 node types
- Pipeline CRUD and run management
- React Flow editor integration

#### WS16 — Copilot Agent
- Agentic media copilot with Claude API integration
- WebSocket streaming endpoint (`/ws/agents/stream`)
- Agent memory system with importance scoring and expiration
- Skill packs for media operations
- Agent CRUD endpoints

#### WS17 — Audio Transform
- Audio transform service: denoise, silence removal, pitch shift, time stretch, loudness normalization, EQ presets
- Speech enhance convenience chain
- Generic chain runner for composable transforms
- REST endpoints for all audio transforms

#### WS18 — Video Transform
- Video transform studio: background removal, super resolution, style transfer, auto crop, thumbnail generation
- Before/after slider component
- REST endpoints for all video transforms

#### WS19 — Frontend Dashboard
- Next.js 14 frontend with 16 dashboard pages
- Sidebar navigation linking to all modules
- Zustand auth store and React Query provider
- Train page with Models, Experiments, and Datasets tabs
- Transform page with Audio and Video tabs
- Dataset management UI with upload, stats, split controls

#### WS20 — Testing & E2E
- Comprehensive test suite with integration tests, API contract tests, and fixtures
- Test utilities module with synthetic image/audio generators
- Enhanced conftest.py with fixtures for test_app, test_image, test_audio, auth_headers
- Sample JSON fixtures for pipeline, experiment config, and alert rules
- Integration tests: vision pipeline, audio pipeline, model lifecycle, search, auth flow
- pytest configuration with markers (unit, integration, e2e, slow)
- Coverage configuration with 50% minimum threshold
- GitHub Actions CI workflow with PostgreSQL and Redis services
- Makefile targets: dev, build, stop, clean, logs, test, test-unit, test-integration, test-coverage, lint

## [0.1.0] - 2026-03-20

### Added
- Initial project scaffold with full directory structure
