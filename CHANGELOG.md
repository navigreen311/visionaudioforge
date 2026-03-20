# Changelog

## [0.2.0] - 2026-03-20

### Changed
- Replaced stub docker-compose.yml with production-ready configuration (7 services)
- Upgraded backend Dockerfile to multi-stage build with non-root user (appuser)
- Upgraded frontend Dockerfile to multi-stage build (builder + standalone production)
- Enhanced nginx.conf with gzip compression and security headers (X-Frame-Options, X-Content-Type-Options)
- Replaced .env.example with streamlined production variables (DATABASE_URL, REDIS_URL, JWT, Celery, MinIO)
- Simplified setup.sh to minimal bootstrap script
- Rewrote Makefile with dev, build, stop, clean, logs, db-shell, redis-shell targets

### Added
- scripts/init-db.sql with PostgreSQL extensions (vector, pg_trgm, uuid-ossp)
- Health checks on db (pg_isready), redis (redis-cli ping), minio (curl health endpoint)
- Hot-reload volume mounts for backend and frontend services
- Celery worker service with redis/db health dependencies

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
