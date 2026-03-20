# Changelog

## [1.0.0] - 2026-03-20

### Added
- Health endpoint (`GET /api/health`) with real DB, Redis, and MinIO probes; returns structured status with per-service latency, uptime, and ISO-8601 timestamp
- Structured JSON logging via `python-json-logger` with contextual fields (request_id, user_id, workspace_id, method, path, status_code, duration_ms)
- Request ID middleware — generates UUID per request, propagates via `X-Request-ID` header and contextvars
- Timing middleware — measures request duration, adds `X-Process-Time` header, logs method/path/status/duration
- Prometheus metrics module with `http_requests_total`, `http_request_duration_seconds`, `ws_active_connections`, and `inference_queue_depth`
- Metrics endpoint (`GET /api/metrics`) serving Prometheus text exposition format
- Tests for health response shape, middleware headers, and metrics endpoint

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
