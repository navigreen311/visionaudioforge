# Changelog

## [0.2.0] - 2026-03-20

### Added
- Visual Pipeline Builder (M16) with drag-and-drop React Flow editor
- 21 pipeline node types across 6 categories (Input, Vision, Audio, Search, Action, Transform)
- Pipeline execution engine with topological sort (Kahn's algorithm) and cycle detection
- Node registry with BaseNode abstract class and per-node input/output schemas
- API endpoints: create, list, get, validate, run pipelines; list node types; get run results
- Celery task for asynchronous pipeline execution
- Frontend: NodePalette (categorized accordion), PipelineCanvas (React Flow), NodeConfig (dynamic forms)
- Pipeline run history panel with status, duration, and timestamps
- Pydantic schemas for all pipeline request/response models
- Unit and integration tests for engine, registry, and API

## [0.1.0] - 2026-03-20

### Added
- Initial project scaffold with full directory structure
- Docker Compose configuration with 7 services (API, Frontend, DB, Redis, MinIO, NGINX, Celery)
- FastAPI backend with stub routes for all 15 API modules
- SQLAlchemy models for all domain entities (User, Workspace, Model, Experiment, Dataset, Asset, Pipeline, Alert, Embedding, Event, AuditLog, Agent)
- Next.js 14 frontend with 16 dashboard pages (all stubs)
- Sidebar navigation linking to all modules
- Zustand auth store and React Query provider setup
- Alembic migration infrastructure
- NGINX reverse proxy configuration
- Health check endpoint
