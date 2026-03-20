# Changelog

## [0.2.0] - 2026-03-20

### Added
- JWT authentication with access tokens (30 min) and refresh tokens (7 days) via python-jose HS256
- Password hashing with passlib bcrypt (hash_password, verify_password)
- AuthService with register, login, refresh, and user lookup methods
- Auth routes: POST /api/auth/register, /login, /refresh; GET /me; PUT /me
- Pydantic schemas for auth requests/responses (LoginRequest, RegisterRequest, TokenResponse, UserResponse)
- FastAPI dependencies: get_current_user (Bearer token), require_role (RBAC factory), get_current_workspace
- AuditMiddleware logging user_id, HTTP method, path, and IP to audit_logs table (non-blocking background task)
- Comprehensive test suite (test_auth.py): password hashing, token lifecycle, route integration, RBAC enforcement

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
