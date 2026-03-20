# Changelog

## [0.2.0] - 2026-03-20

### Added
- Audio spectral analysis service (STFT, Mel spectrogram, MFCC, power spectrogram)
- Audio I/O utilities (load, save, base64 encode, validate with size/duration limits)
- Visualization module generating base64 PNG plots (spectrogram, Mel, MFCC, waveform)
- POST /api/audio/analyze endpoint with selectable operations
- Pydantic schemas for audio analysis request/response
- Comprehensive test suite for spectral analysis, I/O, visualization, and API
- Documentation for audio spectral analysis feature
- matplotlib dependency for headless plot rendering

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
