# Changelog

## [0.2.0] - 2026-03-20

### Added
- Comprehensive test suite with integration tests, API contract tests, and fixtures
- Test utilities module (`backend/tests/utils.py`) with synthetic image/audio generators and assertion helpers
- Enhanced `conftest.py` with fixtures for test_app, test_image, test_audio, auth_headers
- Sample JSON fixtures for pipeline, experiment config, and alert rules
- Integration tests: vision pipeline, audio pipeline, model lifecycle, search, auth flow
- API contract tests: endpoint existence validation and error format verification
- pytest configuration with markers (unit, integration, e2e, slow) in `pyproject.toml`
- Coverage configuration with 50% minimum threshold
- GitHub Actions CI workflow with PostgreSQL and Redis services
- Makefile targets: test, test-unit, test-integration, test-coverage, lint
- Testing documentation (`docs/testing.md`)
- Stub endpoints for `GET /api/auth/me` and `GET /api/search/stats`

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
