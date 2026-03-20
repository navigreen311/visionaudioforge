# Model Registry (M6)

## Overview

The Model Registry provides versioned lifecycle management for ML models. It tracks model metadata, metrics, and status transitions from registration through production deployment.

## Architecture

```
Frontend (Train page)
  |
  v
API Routes (/api/registry/*)
  |
  v
ModelRegistryService (business logic)
  |
  v
ModelRecord (SQLAlchemy ORM) -> PostgreSQL
```

## Model Lifecycle

```
registered --> staging --> production --> archived
    |             |                         ^
    +-------------+-------------------------+
              (any state -> archived)
```

Valid transitions:
- `registered` -> `staging` | `archived`
- `staging` -> `production` | `archived`
- `production` -> `archived`
- Rollback can restore any version to `production`

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/registry/register` | Register a new model |
| GET | `/api/registry/models` | List models (paginated, filterable) |
| GET | `/api/registry/models/{id}` | Get model by ID |
| PUT | `/api/registry/models/{id}/status` | Update model status |
| POST | `/api/registry/compare` | Compare two models' metrics |
| POST | `/api/registry/models/{id}/rollback` | Rollback to a prior version |

### Query Parameters (GET /models)

| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `workspace_id` | UUID | Yes | — | Filter by workspace |
| `status` | string | No | — | Filter by status |
| `skip` | int | No | 0 | Pagination offset |
| `limit` | int | No | 20 | Page size (max 100) |

### Request/Response Examples

**Register Model:**
```json
POST /api/registry/register
{
  "name": "resnet50-classifier",
  "version": "1.0.0",
  "backbone": "ResNet50",
  "metrics": {"accuracy": 0.95, "f1": 0.92},
  "workspace_id": "uuid-here"
}
```

**Compare Models:**
```json
POST /api/registry/compare
{
  "model_a_id": "uuid-a",
  "model_b_id": "uuid-b"
}
// Response includes metric_diffs with per-key diff values
```

## Key Files

- `backend/app/services/models/registry.py` — Service layer
- `backend/app/api/routes/registry.py` — API routes
- `backend/app/schemas/registry.py` — Pydantic schemas
- `backend/app/models/model_registry.py` — SQLAlchemy model
- `frontend/src/app/(dashboard)/train/page.tsx` — Frontend UI
- `frontend/src/lib/api.ts` — API client functions
- `backend/tests/test_model_registry.py` — Tests

## Running Tests

```bash
cd backend
pytest tests/test_model_registry.py -v
```

## Environment Variables

No additional environment variables required. Uses existing database connection from `settings.DATABASE_URL`.
