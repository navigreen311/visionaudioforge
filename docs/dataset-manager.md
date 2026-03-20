# Dataset Manager (M7)

## Overview

The Dataset Manager provides end-to-end dataset lifecycle management for
Vision & Audio AI workflows. It covers dataset creation, sample upload to
MinIO object storage, statistics computation, train/val/test splitting, and
JSON export.

## Architecture

```
Frontend (React)                  Backend (FastAPI)                Storage
┌────────────────┐    REST    ┌─────────────────────┐         ┌───────┐
│ Train Page     │ ────────── │ /api/datasets/*     │ ──────> │ MinIO │
│  └ Datasets Tab│            │   └ DatasetService  │         └───────┘
└────────────────┘            │   └ MinIOStorage    │         ┌────────┐
                              │                     │ ──────> │Postgres│
                              └─────────────────────┘         └────────┘
```

### Key Components

| Layer     | File                                              | Purpose                          |
|-----------|---------------------------------------------------|----------------------------------|
| Model     | `backend/app/models/dataset.py`                   | Dataset SQLAlchemy model         |
| Model     | `backend/app/models/asset.py`                     | Asset (sample) SQLAlchemy model  |
| Storage   | `backend/app/services/data/storage.py`            | MinIO SDK wrapper                |
| Service   | `backend/app/services/data/dataset_manager.py`    | Business logic                   |
| Schemas   | `backend/app/schemas/dataset.py`                  | Pydantic request/response models |
| Routes    | `backend/app/api/routes/datasets.py`              | FastAPI endpoints                |
| Frontend  | `frontend/src/app/(dashboard)/train/page.tsx`     | Datasets tab UI                  |
| Tests     | `backend/tests/test_dataset_manager.py`           | Unit + integration tests         |

## API Endpoints

| Method | Path                          | Description               |
|--------|-------------------------------|---------------------------|
| POST   | `/api/datasets`               | Create a new dataset      |
| GET    | `/api/datasets?workspace_id=` | List datasets (paginated) |
| GET    | `/api/datasets/{id}`          | Get dataset with stats    |
| POST   | `/api/datasets/{id}/upload`   | Upload sample files       |
| POST   | `/api/datasets/{id}/split`    | Split into train/val/test |
| POST   | `/api/datasets/{id}/stats`    | Recompute statistics      |
| GET    | `/api/datasets/{id}/export`   | Download metadata JSON    |

## Environment Variables

| Variable           | Default        | Description               |
|--------------------|----------------|---------------------------|
| `MINIO_ENDPOINT`   | `minio:9000`   | MinIO server address      |
| `MINIO_ACCESS_KEY` | `minioaccess`  | MinIO access key          |
| `MINIO_SECRET_KEY` | `miniosecret`  | MinIO secret key          |
| `MINIO_BUCKET`     | `visionaudioforge` | Default bucket name   |

The dataset manager uses the bucket `vaf-datasets` for all sample storage.

## Running Tests

```bash
cd backend
pytest tests/test_dataset_manager.py -v
```

## Frontend Usage

1. Navigate to the **Train** page in the dashboard sidebar.
2. Click the **Datasets** tab.
3. Click **Create Dataset** to open the creation modal.
4. After creating a dataset, click its row to open the detail view.
5. Use the drag-and-drop upload zone to add samples.
6. View computed statistics and label distribution chart.
7. Adjust train/val/test sliders and click **Split Dataset**.
8. Click **Export JSON** to download the dataset manifest.
