# Changelog

All notable changes to VisionAudioForge are documented in this file.

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
- Project configuration and CLAUDE.md
