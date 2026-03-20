# API Reference

Base URL: `http://localhost:8000`

Interactive docs: [Swagger UI](http://localhost:8000/docs) | [ReDoc](http://localhost:8000/redoc)

## Endpoints

### Health & Metrics

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| GET | `/api/health` | Service health with dependency checks | No | Active |
| GET | `/api/metrics` | Prometheus metrics | No | Active |

### Authentication

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/auth/login` | Login with credentials, returns JWT | No | Active |
| POST | `/api/auth/register` | Register new user | No | Active |
| GET | `/api/auth/me` | Get current user profile | Yes | Active |

### Vision

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/vision/analyze` | Analyze uploaded image | Yes | Active |
| POST | `/api/vision/optical-flow` | Compute optical flow between frames | Yes | Active |
| POST | `/api/vision/frame-diff` | Frame differencing for motion detection | Yes | Active |
| POST | `/api/vision/screen-analyze` | Analyze screen capture | Yes | Active |
| POST | `/api/vision/detect` | Object detection (YOLO) | Yes | Active |
| POST | `/api/vision/ocr` | OCR text extraction | Yes | Active |
| POST | `/api/vision/error-analysis` | Confusion matrix and quality reports | Yes | Active |

### Audio

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/audio/analyze` | Spectral analysis of audio file | Yes | Active |
| POST | `/api/audio/augment` | Audio augmentation pipeline | Yes | Active |

### Transforms

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/transform/audio/denoise` | Denoise audio | Yes | Active |
| POST | `/api/transform/audio/silence-remove` | Remove silence | Yes | Active |
| POST | `/api/transform/audio/pitch-shift` | Pitch shift audio | Yes | Active |
| POST | `/api/transform/audio/time-stretch` | Time stretch audio | Yes | Active |
| POST | `/api/transform/audio/eq` | Apply EQ preset | Yes | Active |
| POST | `/api/transform/audio/chain` | Run composable transform chain | Yes | Active |
| POST | `/api/transform/video/background-remove` | Remove video background | Yes | Active |
| POST | `/api/transform/video/super-resolution` | Upscale video | Yes | Active |
| POST | `/api/transform/video/style` | Apply style transfer | Yes | Active |
| POST | `/api/transform/video/auto-crop` | Auto crop video | Yes | Active |
| POST | `/api/transform/video/thumbnail` | Generate thumbnail | Yes | Active |

### Transfer Learning

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/transfer/start` | Start transfer learning job | Yes | Active |

### Experiments

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| GET | `/api/experiments` | List experiments | Yes | Active |
| POST | `/api/experiments` | Create experiment | Yes | Active |
| GET | `/api/experiments/{id}` | Get experiment details | Yes | Active |
| POST | `/api/experiments/{id}/epochs` | Record epoch metrics | Yes | Active |
| GET | `/api/experiments/{id}/best` | Get best epoch | Yes | Active |
| POST | `/api/experiments/compare` | Compare experiments | Yes | Active |

### Model Registry

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/registry/register` | Register a new model | Yes | Active |
| GET | `/api/registry/models` | List models | Yes | Active |
| GET | `/api/registry/models/{id}` | Get model details | Yes | Active |
| PUT | `/api/registry/models/{id}/status` | Update model lifecycle status | Yes | Active |
| POST | `/api/registry/compare` | Compare models | Yes | Active |
| POST | `/api/registry/models/{id}/rollback` | Rollback model version | Yes | Active |

### Search

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/search/query` | Cross-modal search with CLIP embeddings | Yes | Active |
| GET | `/api/search/stats` | Search index statistics | Yes | Active |

### Pipeline

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| GET | `/api/pipeline/nodes` | List available node types | Yes | Active |
| POST | `/api/pipeline/validate` | Validate pipeline definition | Yes | Active |
| POST | `/api/pipeline/create` | Create pipeline | Yes | Active |
| GET | `/api/pipelines` | List pipelines | Yes | Active |
| GET | `/api/pipelines/{id}` | Get pipeline details | Yes | Active |
| POST | `/api/pipeline/run/{id}` | Start pipeline run | Yes | Active |
| GET | `/api/pipeline/runs/{id}` | Get run status | Yes | Active |

### Alerts

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/alerts/rules` | Create alert rule | Yes | Active |
| GET | `/api/alerts` | List alerts | Yes | Active |

### Agents

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/agents/chat` | Send message to AI copilot | Yes | Active |
| GET | `/api/agents` | List agents | Yes | Active |
| POST | `/api/agents` | Create agent | Yes | Active |
| GET | `/api/agents/{id}/memory` | Get agent memory | Yes | Active |
| POST | `/api/agents/{id}/memory/decay` | Trigger memory decay | Yes | Active |
| DELETE | `/api/agents/{id}/memory/{mid}` | Delete memory entry | Yes | Active |

### Assets

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| GET | `/api/assets` | List assets | Yes | Active |
| POST | `/api/assets/upload` | Upload asset to MinIO | Yes | Active |

### Datasets

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/datasets` | Create dataset | Yes | Active |
| GET | `/api/datasets` | List datasets | Yes | Active |
| GET | `/api/datasets/{id}` | Get dataset details | Yes | Active |
| POST | `/api/datasets/{id}/upload` | Upload files to dataset | Yes | Active |
| POST | `/api/datasets/{id}/split` | Split dataset (train/val/test) | Yes | Active |
| POST | `/api/datasets/{id}/stats` | Compute dataset statistics | Yes | Active |
| GET | `/api/datasets/{id}/export` | Export dataset | Yes | Active |

### Safety

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| POST | `/api/safety/scan` | Scan content for safety | Yes | Active |

### Workspaces

| Method | Path | Description | Auth | Status |
|--------|------|-------------|------|--------|
| GET | `/api/workspaces` | List workspaces | Yes | Active |
| POST | `/api/workspaces` | Create workspace | Yes | Active |

### WebSocket Endpoints

| Path | Description |
|------|-------------|
| `/ws/live/stream/{session_id}` | Live video capture with per-frame analysis |
| `/ws/agents/stream` | Streaming copilot chat |
