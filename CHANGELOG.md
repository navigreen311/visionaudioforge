# Changelog

## [0.2.0] - 2026-03-20

### Added
- FAISS cross-modal search with CLIP embeddings (M13)
- `EmbeddingService` — CLIP-based image/text embedding with lazy model loading and fallback mode
- `FAISSIndexService` — FAISS vector index with flat (exact) and IVF (approximate) search support
- `CrossModalSearchService` — high-level search orchestrator with text, image, and similarity search
- Search API routes: `POST /api/search/query`, `POST /api/search/index`, `GET /api/search/stats`
- Frontend search page with modality toggle (Text / Image / Audio), drag-drop upload, results grid, and preview modal
- Frontend components: `SearchBar`, `ResultsGrid`, `ResultCard`
- Unit and integration tests for embeddings, FAISS indexing, search service, and API endpoints
- Documentation: `docs/faiss-search.md`

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
