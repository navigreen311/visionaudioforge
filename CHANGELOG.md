# Changelog

## [0.2.0] - 2026-03-20

### Added
- Object detection service (`ObjectDetector`) with YOLOv8 and graceful ImportError fallback
- OCR service (`OCREngine`) with pytesseract and stub fallback
- Systematic error analysis: confusion matrix, per-class metrics, top confusions, quality reports
- API endpoints: `POST /api/vision/detect`, `/api/vision/ocr`, `/api/vision/error-analysis`
- Comprehensive test suite for detection, OCR, error analysis, and API routes
- Documentation at `docs/vision-detection.md`

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
