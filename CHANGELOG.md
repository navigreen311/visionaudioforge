# Changelog

## [0.2.0] - 2026-03-20

### Added
- Complete SQLAlchemy models with UUIDMixin, TimestampMixin, proper Enums, relationships, and indexes
- Alembic initial migration (001_initial_schema) creating all 14 tables with foreign keys and indexes
- Pydantic schemas for all domain entities (User, Workspace, Model, Experiment, Dataset, Asset, Pipeline, Alert, Agent)
- Common schemas: PaginatedResponse (generic), ErrorResponse, SuccessResponse
- Model tests verifying table names, columns, and constraints
- Schema tests validating both valid and invalid inputs

### Changed
- Refactored base.py: separated UUIDMixin from TimestampMixin for flexible composition
- Updated alembic.ini with corrected database URL
- Replaced string-based status/role/type columns with proper SQLAlchemy Enums
- Standardized field names across models to match API spec (e.g., conditions/actions on AlertRule, modality on Dataset)

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
