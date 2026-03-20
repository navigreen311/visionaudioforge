# Changelog

## [0.2.0] - 2026-03-20

### Added
- Vision preprocessing service (`ImagePreprocessor`) with min-max, z-score, and per-channel normalization
- Color-space conversion support (RGB, BGR, HSV, LAB, grayscale) via OpenCV
- Histogram equalization, edge detection (Canny, Sobel, Laplacian), and aspect-preserving resize
- Configurable preprocessing pipeline that chains operations sequentially
- Vision utility functions: base64 encode/decode, image stats, file validation
- `POST /api/vision/analyze` endpoint for applying preprocessing pipelines to uploaded images
- `POST /api/vision/screen-analyze` endpoint for screenshot visual analysis (brightness, edge density, dominant colors)
- Pydantic schemas for vision API requests/responses
- Comprehensive test suite for all preprocessing operations and utilities
- Vision preprocessing documentation with API reference and usage examples

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
