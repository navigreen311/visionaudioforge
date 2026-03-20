# Changelog

## [0.2.0] - 2026-03-20

### Added
- Live capture engine (M1) with WebSocket streaming
- CaptureWebSocket handler with per-frame analysis (brightness, motion detection, resolution)
- Channel-based ConnectionManager replacing the previous stub
- CaptureSessionManager for in-memory session lifecycle tracking
- WebSocket route at `/ws/live/stream/{session_id}`
- Full capture UI with Camera, Screen, and Microphone source tabs
- LiveFeedPanel component with video display and AI overlay canvas
- AudioMeter component with real-time frequency visualization
- SourceSwitcher and CaptureControls components
- Status bar showing connection status, FPS, frame count, and session duration
- Frame streaming to backend at 5 FPS via WebSocket
- Snapshot download functionality
- Backend tests for ConnectionManager, CaptureSessionManager, and WebSocket frame processing

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
