# Changelog

## [0.2.0] - 2026-03-20

### Added
- Audio augmentation pipeline service (`AudioAugmenter`) with noise injection (white/pink/brown), time stretch, pitch shift, time shift, and SpecAugment masking
- Five augmentation presets: speech_robust, music_robust, environmental, light, heavy
- POST `/api/audio/augment` endpoint accepting file upload with preset or custom JSON pipeline config
- Pydantic schemas for augmentation steps, config, and response
- Unit and integration tests for all augmentation methods and API endpoint
- Documentation at `docs/audio-augmentation.md`

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
