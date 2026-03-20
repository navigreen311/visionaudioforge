# Changelog

## [0.2.0] - 2026-03-20

### Added
- Optical flow services: Lucas-Kanade (sparse) and Farneback (dense) via `MotionAnalyzer`
- Frame differencing: consecutive two-frame and three-frame methods with morphological cleanup
- Motion visualization: flow arrows, HSV heatmaps, flow-to-RGB conversion, motion mask overlays
- `POST /api/vision/optical-flow` endpoint (supports `lucas-kanade` and `farneback` methods)
- `POST /api/vision/frame-diff` endpoint (supports `consecutive` and `three-frame` methods)
- Pydantic schemas: `OpticalFlowResponse`, `FrameDiffResponse`, `MotionStats`
- Comprehensive test suite for motion analysis (unit + API integration)
- Documentation at `docs/vision-motion.md`

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
