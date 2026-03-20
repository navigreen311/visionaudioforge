# Changelog

## [0.2.0] - 2026-03-20

### Added
- Experiment Tracker service (`ExperimentService`) with full CRUD, epoch logging, best-checkpoint selection, and multi-experiment comparison
- Transfer Learning service (`TransferLearningService`) with real PyTorch training loop supporting ResNet-18/50, layer freezing, gradient clipping, and early stopping
- Celery task (`run_finetune_task`) for background fine-tuning execution
- API routes for experiments: list, create, get, log epoch, best checkpoint, compare
- API route for transfer learning: start fine-tune job
- Frontend Train page with experiment list table, training curves chart, comparison overlay, and Start Training modal
- Updated Experiment/ExperimentEpoch models with relationships, best_epoch, error_message, accuracy fields
- Unit and integration tests for experiment tracker (`test_experiment_tracker.py`)
- Documentation (`docs/experiment-tracker.md`)

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
