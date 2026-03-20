# Changelog

## [0.2.0] - 2026-03-20

### Added
- Shared UI component library: Button, Card, Badge, Modal, DataTable, FileUpload, Tabs, Toast/useToast, LoadingSpinner, SkeletonLoader, EmptyState, StatusIndicator
- Responsive dashboard layout with collapsible sidebar, top bar with breadcrumbs, search, notifications, and user dropdown
- Dashboard home page with stats cards, recent activity feed, quick actions, system health, and module status grid
- Login and Register auth pages with form validation and zustand auth integration
- Settings page with tabbed UI: General, API Keys, Users, Integrations
- Enhanced auth store with login/register/initialize actions and localStorage persistence
- Enhanced providers with QueryClient (30s stale, retry 1), ToastProvider, and AuthGuard redirect
- Mobile-responsive sidebar with hamburger toggle

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
