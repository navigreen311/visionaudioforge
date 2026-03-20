# Experiment Tracker

## Overview

The Experiment Tracker manages ML training experiments end-to-end: creation, epoch logging, completion, failure handling, best-checkpoint selection, and multi-experiment comparison. It integrates with a Transfer Learning service that runs real PyTorch fine-tuning loops via Celery background tasks.

## Architecture

```
Frontend (Train page)
  |
  v
API Routes (/api/experiments, /api/transfer)
  |
  v
ExperimentService          TransferLearningService
  |                            |
  v                            v
Experiment / ExperimentEpoch   PyTorch training loop
(PostgreSQL via SQLAlchemy)    (Celery worker)
```

## Data Model

### Experiment
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| name | VARCHAR(255) | Experiment name |
| status | VARCHAR(50) | created / running / completed / failed |
| config | JSON | Training configuration |
| workspace_id | UUID FK | Parent workspace |
| model_id | UUID FK (nullable) | Associated model |
| best_epoch | INT (nullable) | Epoch with lowest val_loss |
| error_message | VARCHAR(1000) | Error details if failed |

### ExperimentEpoch
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| experiment_id | UUID FK | Parent experiment |
| epoch_number | INT | Epoch index (1-based) |
| train_loss | FLOAT | Training loss |
| val_loss | FLOAT | Validation loss |
| accuracy | FLOAT | Training accuracy |
| val_accuracy | FLOAT | Validation accuracy |
| metrics | JSON | Full metrics dict |

## API Endpoints

### Experiments

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/experiments?workspace_id=&model_id=` | List experiments (paginated) |
| POST | `/api/experiments` | Create experiment |
| GET | `/api/experiments/{id}` | Get experiment with epochs |
| POST | `/api/experiments/{id}/epochs` | Log epoch metrics |
| GET | `/api/experiments/{id}/best?metric=val_loss&mode=min` | Get best checkpoint |
| POST | `/api/experiments/compare` | Compare multiple experiments |

### Transfer Learning

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/transfer/start` | Start fine-tuning job |

## Transfer Learning Service

Supports ResNet-18 and ResNet-50 backbones with:
- Layer freezing (freeze all except final classifier)
- Gradient clipping (`torch.nn.utils.clip_grad_norm_`)
- Early stopping (patience-based on val_loss)
- V1 uses synthetic data; production will load real datasets from `dataset_path`

## Frontend

The Train page provides:
- **Experiment list table**: name, status badge, best metric, epoch count
- **Detail view**: training curves chart (loss, val_loss, accuracy)
- **Compare view**: overlay val_loss curves on same chart with side-by-side metrics table
- **Start Training modal**: configure backbone, epochs, learning rate, batch size, freeze layers, gradient clip, early stopping patience

## Environment Variables

No new environment variables required. Uses existing `DATABASE_URL`, `CELERY_BROKER_URL`, and `TORCH_DEVICE` from project config.

## Running Tests

```bash
cd backend
pytest tests/test_experiment_tracker.py -v
```
