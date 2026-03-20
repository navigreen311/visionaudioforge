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

### Annotations (V3)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/annotations` | Create annotation | Yes | V3 |
| GET | `/api/annotations` | Get annotations for asset | Yes | V3 |
| PUT | `/api/annotations/{id}` | Update annotation | Yes | V3 |
| DELETE | `/api/annotations/{id}` | Delete annotation | Yes | V3 |
| GET | `/api/datasets/{id}/annotations` | Get dataset annotations | Yes | V3 |
| POST | `/api/datasets/{id}/annotations/export` | Export annotations (COCO/YOLO/VOC) | Yes | V3 |
| POST | `/api/datasets/{id}/annotations/import` | Import annotations | Yes | V3 |
| GET | `/api/datasets/{id}/annotations/stats` | Annotation statistics | Yes | V3 |

### Governance (V3)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/governance/api-keys` | Create API key | Yes | V3 |
| GET | `/governance/api-keys` | List API keys | Yes | V3 |
| DELETE | `/governance/api-keys/{id}` | Revoke API key | Yes | V3 |
| POST | `/governance/api-keys/{id}/rotate` | Rotate API key | Yes | V3 |
| GET | `/governance/sso/config` | Get SSO configuration | Yes | V3 |
| POST | `/governance/sso/login` | Initiate SSO login | No | V3 |
| GET | `/governance/permissions/{role}` | Get role permissions | No | V3 |
| GET | `/governance/billing/usage` | Get billing usage | Yes | V3 |
| GET | `/governance/billing/dashboard` | Get billing dashboard | Yes | V3 |
| POST | `/governance/billing/upgrade` | Upgrade plan | Yes | V3 |
| GET | `/governance/features` | Get enabled features | Yes | V3 |

### Observability (V3)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/observability/dashboard` | System overview | Yes | V3 |
| GET | `/api/observability/pipeline-health` | Pipeline execution metrics | Yes | V3 |
| GET | `/api/observability/inference` | ML inference metrics | Yes | V3 |
| GET | `/api/observability/errors` | Error taxonomy | Yes | V3 |
| GET | `/api/observability/queues` | Queue metrics | Yes | V3 |
| GET | `/api/observability/sla` | SLA compliance check | Yes | V3 |
| POST | `/api/observability/sla/report` | Generate SLA report | Yes | V3 |
| GET | `/api/observability/alert-fatigue` | Alert fatigue analysis | Yes | V3 |

### Runtime Orchestrator (V3)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/runtime/gpu` | GPU device status | Yes | V3 |
| POST | `/api/runtime/route` | Route model request | Yes | V3 |
| GET | `/api/runtime/cost/{workspace_id}` | Cost report | Yes | V3 |
| GET | `/api/runtime/quota/{workspace_id}` | Quota status | Yes | V3 |
| POST | `/api/runtime/quota` | Set quota | Yes | V3 |
| GET | `/api/runtime/cache/stats` | Cache statistics | Yes | V3 |
| POST | `/api/runtime/cache/clear` | Clear cache | Yes | V3 |
| GET | `/api/runtime/schedule` | Job queue | Yes | V3 |

### Integration Hub (V3)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/integrations/slack/send` | Send Slack message | Yes | V3 |
| POST | `/api/integrations/teams/send` | Send Teams message | Yes | V3 |
| POST | `/api/integrations/email/send` | Send email | Yes | V3 |
| POST | `/api/integrations/webhooks` | Register webhook | Yes | V3 |
| GET | `/api/integrations/webhooks` | List webhooks | Yes | V3 |
| DELETE | `/api/integrations/webhooks/{id}` | Delete webhook | Yes | V3 |
| POST | `/api/integrations/webhooks/{id}/test` | Test webhook | Yes | V3 |
| POST | `/api/integrations/storage/test` | Test storage connector | Yes | V3 |
| GET | `/api/integrations/events` | List events | Yes | V3 |

### Knowledge Graph (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/knowledge-graph/nodes` | Add a node | Yes | V4 |
| GET | `/api/knowledge-graph/nodes` | List nodes | Yes | V4 |
| GET | `/api/knowledge-graph/nodes/{id}` | Get node | Yes | V4 |
| POST | `/api/knowledge-graph/edges` | Add an edge | Yes | V4 |
| GET | `/api/knowledge-graph/edges` | List edges | Yes | V4 |
| GET | `/api/knowledge-graph/nodes/{id}/neighbors` | Get node neighbors | Yes | V4 |
| POST | `/api/knowledge-graph/scene-extract` | Extract entities from scene | Yes | V4 |

### Semantic Memory (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/semantic-memory/store` | Store a memory | Yes | V4 |
| POST | `/api/semantic-memory/recall` | Recall memories by query | Yes | V4 |
| POST | `/api/semantic-memory/decay` | Apply decay to memories | Yes | V4 |
| POST | `/api/semantic-memory/promote/{id}` | Promote a memory | Yes | V4 |
| GET | `/api/semantic-memory/memories` | List all memories | Yes | V4 |

### Command Center (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/command-center/streams` | Add video stream | Yes | V4 |
| GET | `/api/command-center/streams` | List streams | Yes | V4 |
| POST | `/api/command-center/layout` | Set dashboard layout | Yes | V4 |
| GET | `/api/command-center/layout` | Get current layout | Yes | V4 |
| POST | `/api/command-center/shifts` | Create operator shift | Yes | V4 |
| GET | `/api/command-center/shifts` | List shifts | Yes | V4 |
| GET | `/api/command-center/dashboard` | Get dashboard summary | Yes | V4 |

### Simulation Lab (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/simulation/scenarios` | Generate scenario | Yes | V4 |
| GET | `/api/simulation/scenarios` | List scenarios | Yes | V4 |
| GET | `/api/simulation/scenarios/{id}` | Get scenario | Yes | V4 |
| POST | `/api/simulation/run` | Run simulation | Yes | V4 |
| GET | `/api/simulation/report/{id}` | Get simulation report | Yes | V4 |

### ReviewOps (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/reviewops/tasks` | Create review task | Yes | V4 |
| GET | `/api/reviewops/tasks` | List tasks | Yes | V4 |
| GET | `/api/reviewops/tasks/{id}` | Get task | Yes | V4 |
| POST | `/api/reviewops/tasks/{id}/assign` | Assign reviewer | Yes | V4 |
| POST | `/api/reviewops/tasks/{id}/review` | Submit review | Yes | V4 |
| GET | `/api/reviewops/tasks/{id}/status` | Check task status | Yes | V4 |

### Edge Export (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/edge/export` | Export model to edge format | Yes | V4 |
| GET | `/api/edge/exports` | List exports | Yes | V4 |
| GET | `/api/edge/exports/{id}` | Get export details | Yes | V4 |
| GET | `/api/edge/formats` | List supported formats | Yes | V4 |

### Fleet Manager (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/fleet/devices` | Register edge device | Yes | V4 |
| GET | `/api/fleet/devices` | List devices | Yes | V4 |
| GET | `/api/fleet/devices/{id}` | Get device details | Yes | V4 |
| POST | `/api/fleet/devices/{id}/heartbeat` | Device heartbeat | Yes | V4 |
| GET | `/api/fleet/health` | Fleet health summary | Yes | V4 |

### Vertical Packs (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/verticals/packs` | List vertical packs | No | V4 |
| GET | `/api/verticals/packs/{id}` | Get pack details | No | V4 |
| POST | `/api/verticals/install` | Install vertical pack | Yes | V4 |
| GET | `/api/verticals/installed` | List installed packs | Yes | V4 |
| GET | `/api/verticals/packs/{id}/resources` | Get pack resources | Yes | V4 |

### Federated Learning (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/federated/federations` | Create federation | Yes | V4 |
| GET | `/api/federated/federations` | List federations | Yes | V4 |
| GET | `/api/federated/federations/{id}` | Get federation | Yes | V4 |
| POST | `/api/federated/federations/{id}/join` | Join federation | Yes | V4 |
| POST | `/api/federated/federations/{id}/start-round` | Start training round | Yes | V4 |

### Mobile Backend (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/mobile/dashboard` | Mobile dashboard | Yes | V4 |
| POST | `/api/mobile/push/register` | Register push device | Yes | V4 |
| GET | `/api/mobile/push/registrations` | List push registrations | Yes | V4 |
| POST | `/api/mobile/field-notes` | Create field note | Yes | V4 |
| GET | `/api/mobile/field-notes` | List field notes | Yes | V4 |
| GET | `/api/mobile/field-notes/{id}` | Get field note | Yes | V4 |

### Plugin Marketplace (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| POST | `/api/plugins/register` | Register plugin | Yes | V4 |
| GET | `/api/plugins/` | List plugins | Yes | V4 |
| GET | `/api/plugins/{id}` | Get plugin details | Yes | V4 |
| POST | `/api/plugins/{id}/enable` | Enable plugin | Yes | V4 |
| POST | `/api/plugins/{id}/disable` | Disable plugin | Yes | V4 |
| POST | `/api/plugins/{id}/execute` | Execute plugin action | Yes | V4 |
| GET | `/api/plugins/marketplace/featured` | Featured plugins | No | V4 |

### Developer Tools (V4)

| Method | Path | Description | Auth | Phase |
|--------|------|-------------|------|-------|
| GET | `/api/developer/openapi` | Get OpenAPI spec | No | V4 |
| GET | `/api/developer/proto` | Get gRPC proto info | No | V4 |
| GET | `/api/developer/proto/download` | Download proto file | No | V4 |
| POST | `/api/developer/node-templates` | Create node template | Yes | V4 |
| GET | `/api/developer/node-templates` | List node templates | Yes | V4 |
| GET | `/api/developer/sdks` | List available SDKs | No | V4 |
| GET | `/api/developer/health` | Developer tools health | No | V4 |

### WebSocket Endpoints

| Path | Description | Phase |
|------|-------------|-------|
| `/ws/live/stream/{session_id}` | Live video capture with per-frame analysis | V2 |
| `/ws/agents/stream` | Streaming copilot chat | V2 |
