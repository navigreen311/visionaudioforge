# Changelog

## [0.2.0] - 2026-03-20

### Added
- Audio Transform Studio (M4) with full transform chain pipeline
- AudioTransformService: denoise (spectral gating), remove silence, pitch shift, time stretch, loudness normalization, EQ presets (flat/voice/music/podcast), speech enhance chain
- POST /api/transform/audio endpoint accepting file upload + JSON operations list
- Transform page with waveform visualization, preset buttons, custom chain builder, before/after comparison, audio playback, and download
- Comprehensive test suite for all transform operations and API endpoint

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
