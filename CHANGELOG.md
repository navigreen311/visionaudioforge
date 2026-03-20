# Changelog

## [0.2.0] - 2026-03-20

### Added
- Model Registry service (`ModelRegistryService`) with full lifecycle management
- API routes: register, list, get, update status, compare, rollback models
- Model lifecycle transitions: registered -> staging -> production -> archived
- Side-by-side model metric comparison endpoint
- Model rollback with automatic production demotion
- Pydantic schemas for registry API (ModelCreate, ModelRead, StatusUpdate, CompareRequest, RollbackRequest)
- Frontend Train page with Models / Experiments / Datasets tabs
- Models tab: sortable table, status badges, register modal, detail panel, compare view
- React Query integration for model data fetching and mutations
- Frontend API functions: listModels, registerModel, updateModelStatus, compareModels, rollbackModel
- 10 unit/integration tests for model registry service and API endpoints

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
