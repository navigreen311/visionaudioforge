# Changelog

## [0.2.0] - 2026-03-20

### Added
- Dataset Manager (M7) with full CRUD, upload, split, stats, and export
- MinIO storage service (`MinIOStorageService`) for object upload/download/list/delete
- Dataset service (`DatasetService`) with create, upload_samples, list, get, compute_stats, split, delete, export
- API routes: POST/GET /api/datasets, POST upload/split/stats, GET export
- Frontend Datasets tab on Train page with create modal, upload drag-and-drop, stats panel, split controls, export button
- Pydantic schemas for dataset endpoints (`DatasetCreate`, `DatasetRead`, `SplitRequest`, etc.)
- Unit and integration tests for dataset manager (9 tests covering service + API layer)

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
