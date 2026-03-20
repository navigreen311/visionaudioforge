# Changelog

## [0.2.0] - 2026-03-20

### Added
- Agentic Media Copilot with Claude API streaming chat (claude-sonnet-4-20250514)
- CopilotService with streaming responses, tool execution, and mock fallback mode
- AgentMemoryService with store, recall, decay, promote, and clear operations
- 6 copilot tools: search_media, analyze_image, analyze_audio, create_alert, query_events, get_system_status
- 7 skill packs: general, investigator, qa_analyst, compliance, media_editor, operations, executive
- WebSocket endpoint at /ws/agents/stream for real-time token streaming
- REST API endpoints for chat, agent CRUD, and memory management
- Frontend chat interface with streaming display, tool use indicators, and message bubbles
- SkillPackSwitcher component for persona selection
- MemoryPanel component with importance badges and decay controls
- Agent model updated with importance_score, freshness_score, and expires_at fields
- Comprehensive test suite for copilot service, memory, tools, and API routes

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
