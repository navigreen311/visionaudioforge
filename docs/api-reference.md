# API Reference

Base URL: `http://localhost:8000`

Interactive docs: [Swagger UI](http://localhost:8000/docs) | [ReDoc](http://localhost:8000/redoc)

## Endpoints

### Health & Metrics

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/health` | Service health with dependency checks | No | V1 |
| GET | `/api/metrics` | Prometheus metrics | No | V1 |

### Authentication

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/auth/login` | Login with credentials, returns JWT | No | V1 |
| POST | `/api/auth/register` | Register new user | No | V1 |
| GET | `/api/auth/me` | Get current user profile | Yes | V1 |

### Vision

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/vision/analyze` | Analyze uploaded image | Yes | V2 |
| POST | `/api/vision/optical-flow` | Compute optical flow between frames | Yes | V2 |
| POST | `/api/vision/frame-diff` | Frame differencing for motion detection | Yes | V2 |
| POST | `/api/vision/screen-analyze` | Analyze screen capture | Yes | V2 |
| POST | `/api/vision/detect` | Object detection (YOLO) | Yes | V2 |
| POST | `/api/vision/ocr` | OCR text extraction | Yes | V2 |
| POST | `/api/vision/error-analysis` | Confusion matrix and quality reports | Yes | V2 |

### Audio

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/audio/analyze` | Spectral analysis of audio file | Yes | V2 |
| POST | `/api/audio/augment` | Audio augmentation pipeline | Yes | V2 |

### Transforms

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/transform/audio/denoise` | Denoise audio | Yes | V2 |
| POST | `/api/transform/audio/silence-remove` | Remove silence | Yes | V2 |
| POST | `/api/transform/audio/pitch-shift` | Pitch shift audio | Yes | V2 |
| POST | `/api/transform/audio/time-stretch` | Time stretch audio | Yes | V2 |
| POST | `/api/transform/audio/eq` | Apply EQ preset | Yes | V2 |
| POST | `/api/transform/audio/chain` | Run composable transform chain | Yes | V2 |
| POST | `/api/transform/video/background-remove` | Remove video background | Yes | V2 |
| POST | `/api/transform/video/super-resolution` | Upscale video | Yes | V2 |
| POST | `/api/transform/video/style` | Apply style transfer | Yes | V2 |
| POST | `/api/transform/video/auto-crop` | Auto crop video | Yes | V2 |
| POST | `/api/transform/video/thumbnail` | Generate thumbnail | Yes | V2 |

### Transfer Learning

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/transfer/start` | Start transfer learning job | Yes | V2 |

### Experiments

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/experiments` | List experiments | Yes | V2 |
| POST | `/api/experiments` | Create experiment | Yes | V2 |
| GET | `/api/experiments/{id}` | Get experiment details | Yes | V2 |
| POST | `/api/experiments/{id}/epochs` | Record epoch metrics | Yes | V2 |
| GET | `/api/experiments/{id}/best` | Get best epoch | Yes | V2 |
| POST | `/api/experiments/compare` | Compare experiments | Yes | V2 |

### Model Registry

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/registry/register` | Register a new model | Yes | V2 |
| GET | `/api/registry/models` | List models | Yes | V2 |
| GET | `/api/registry/models/{id}` | Get model details | Yes | V2 |
| PUT | `/api/registry/models/{id}/status` | Update model lifecycle status | Yes | V2 |
| POST | `/api/registry/compare` | Compare models | Yes | V2 |
| POST | `/api/registry/models/{id}/rollback` | Rollback model version | Yes | V2 |

### Search

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/search/query` | Cross-modal search with CLIP embeddings | Yes | V2 |
| GET | `/api/search/stats` | Search index statistics | Yes | V2 |

### Pipeline

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/pipeline/nodes` | List available node types | Yes | V2 |
| POST | `/api/pipeline/validate` | Validate pipeline definition | Yes | V2 |
| POST | `/api/pipeline/create` | Create pipeline | Yes | V2 |
| GET | `/api/pipelines` | List pipelines | Yes | V2 |
| GET | `/api/pipelines/{id}` | Get pipeline details | Yes | V2 |
| POST | `/api/pipeline/run/{id}` | Start pipeline run | Yes | V2 |
| GET | `/api/pipeline/runs/{id}` | Get run status | Yes | V2 |

### Alerts

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/alerts/rules` | Create alert rule | Yes | V2 |
| GET | `/api/alerts` | List alerts | Yes | V2 |

### Agents (AI Copilot)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/agents/chat` | Send message to AI copilot | Yes | V2 |
| GET | `/api/agents` | List agents | Yes | V2 |
| POST | `/api/agents` | Create agent | Yes | V2 |
| GET | `/api/agents/{id}/memory` | Get agent memory | Yes | V2 |
| POST | `/api/agents/{id}/memory/decay` | Trigger memory decay | Yes | V2 |
| DELETE | `/api/agents/{id}/memory/{mid}` | Delete memory entry | Yes | V2 |

### Assets

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/assets` | List assets | Yes | V2 |
| POST | `/api/assets/upload` | Upload asset to MinIO | Yes | V2 |

### Datasets

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/datasets` | Create dataset | Yes | V2 |
| GET | `/api/datasets` | List datasets | Yes | V2 |
| GET | `/api/datasets/{id}` | Get dataset details | Yes | V2 |
| POST | `/api/datasets/{id}/upload` | Upload files to dataset | Yes | V2 |
| POST | `/api/datasets/{id}/split` | Split dataset (train/val/test) | Yes | V2 |
| POST | `/api/datasets/{id}/stats` | Compute dataset statistics | Yes | V2 |
| GET | `/api/datasets/{id}/export` | Export dataset | Yes | V2 |

### Safety

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/safety/scan` | Scan content for safety | Yes | V2 |

### Workspaces

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/workspaces` | List workspaces | Yes | V2 |
| POST | `/api/workspaces` | Create workspace | Yes | V2 |

### Capture

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/capture/sessions` | List capture sessions | Yes | V2 |
| POST | `/api/capture/sessions` | Create capture session | Yes | V2 |

### Evaluation Lab (V3)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/evaluation/benchmarks` | Create a benchmark configuration | Yes | V3 |
| POST | `/api/evaluation/benchmarks/{id}/run` | Execute benchmark and return results | Yes | V3 |
| POST | `/api/evaluation/tournament` | Run round-robin model tournament | Yes | V3 |
| POST | `/api/evaluation/threshold-analysis` | Compute metrics across decision thresholds | Yes | V3 |
| GET | `/api/evaluation/scorecard/{model_id}` | Generate model scorecard | Yes | V3 |

### Validation & Drift (V3)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/validate/drift` | Detect data drift (KL, KS, PSI) | Yes | V3 |
| POST | `/api/validate/schema` | Validate dataset schema | Yes | V3 |
| POST | `/api/validate/explain` | Explain model prediction | Yes | V3 |
| POST | `/api/validate/constraints` | Validate input constraints | Yes | V3 |

### Investigation Workspace (V3)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/investigate/cases` | Create investigation case | Yes | V3 |
| GET | `/api/investigate/cases` | List cases in workspace | Yes | V3 |
| GET | `/api/investigate/cases/{id}` | Get case with evidence and notes | Yes | V3 |
| POST | `/api/investigate/cases/{id}/evidence` | Add evidence to case | Yes | V3 |
| POST | `/api/investigate/cases/{id}/notes` | Add note to case | Yes | V3 |
| GET | `/api/investigate/timeline` | Query event timeline | Yes | V3 |
| GET | `/api/investigate/cases/{id}/export` | Export full case as JSON | Yes | V3 |

### WebSocket Endpoints

| Path | Description | Phase |
|------|-------------|-------|
| `/ws/live/stream/{session_id}` | Live video capture with per-frame analysis | V2 |
| `/ws/agents/stream` | Streaming copilot chat | V2 |
