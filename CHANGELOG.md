# Changelog

## [0.2.0] - 2026-03-20

### Added
- Video Transform Studio (M5) with full service, API, frontend, and tests
- `VideoTransformService` with background removal (threshold, grabcut, rembg), super-resolution (2x/4x), style transfer (sketch, edges, cartoon, oil painting), auto-crop, thumbnail generation, frame stabilisation, and scene detection
- Five REST endpoints under `/api/transform/video/*` for background-remove, super-resolution, style, auto-crop, and thumbnail
- Interactive Transform page with Video/Image tab, mode selector, upload zone, and per-mode options
- `BeforeAfterSlider` component for drag-to-compare before/after image results
- Comprehensive test suite (`test_video_transform.py`) covering all service methods and API endpoints
- Documentation at `docs/video-transform.md`

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
