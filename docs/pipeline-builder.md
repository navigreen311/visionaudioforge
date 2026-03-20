# Pipeline Builder (M16)

## Overview

The Pipeline Builder lets users visually compose data-processing pipelines by dragging nodes onto a canvas, connecting them with edges, and executing the resulting graph. It supports vision, audio, search, and action workflows.

## Architecture

```
Frontend (React Flow)          Backend (FastAPI)
┌──────────────────┐           ┌──────────────────────┐
│ NodePalette      │           │ /api/pipeline/nodes   │  ← node catalogue
│ PipelineCanvas   │──HTTP────▶│ /api/pipeline/create  │  ← save pipeline
│ NodeConfig       │           │ /api/pipeline/validate│  ← dry-run validation
│ Run History      │           │ /api/pipeline/run/:id │  ← dispatch execution
└──────────────────┘           │ /api/pipeline/runs/:id│  ← poll results
                               └──────────┬───────────┘
                                          │ Celery task
                                          ▼
                               ┌──────────────────────┐
                               │ PipelineEngine        │
                               │  validate_pipeline()  │
                               │  _topological_sort()  │
                               │  execute_pipeline()   │
                               └──────────────────────┘
```

## Node Categories (21 nodes)

| Category  | Nodes |
|-----------|-------|
| Input     | InputImage, InputAudio, InputVideo |
| Vision    | Normalize, ColorConvert, DetectObjects, OpticalFlow, FrameDiff, EdgeDetect |
| Audio     | STFT, MelSpectrogram, MFCC, AugmentAudio |
| Search    | EmbedCLIP, FAISSSearch |
| Action    | Alert, Webhook, SaveAsset |
| Transform | Resize, Filter, Merge |

## Pipeline Definition Format

```json
{
  "nodes": [
    {"id": "n1", "type": "input_image", "params": {"path": "/data/img.png"}},
    {"id": "n2", "type": "normalize", "params": {"method": "min_max"}}
  ],
  "edges": [
    {"from": "n1", "to": "n2", "from_port": "image", "to_port": "image"}
  ]
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/pipeline/nodes` | List all node types with schemas |
| POST | `/api/pipeline/validate` | Validate a definition (no save) |
| POST | `/api/pipeline/create` | Save a new pipeline |
| GET | `/api/pipelines?workspace_id=` | List pipelines (paginated) |
| GET | `/api/pipelines/{id}` | Get pipeline with definition |
| POST | `/api/pipeline/run/{id}` | Start async execution |
| GET | `/api/pipeline/runs/{run_id}` | Get run status and results |

## Engine Details

- **Validation**: checks node types exist, edges reference valid IDs, no cycles, required params present.
- **Topological sort**: Kahn's algorithm (BFS-based, O(V+E)).
- **Execution**: nodes run in topological order; upstream outputs are mapped to downstream inputs via edge port names.
- **Error handling**: each node catches exceptions and returns `{"error": str}` instead of crashing the pipeline.

## Running Tests

```bash
cd backend
pytest tests/test_pipeline.py -v
```

## Environment Variables

No additional env vars required. Uses existing database, Redis, and Celery configuration from `.env`.

## Key Files

- `backend/app/services/pipeline/nodes.py` — node classes and registry
- `backend/app/services/pipeline/engine.py` — validation and execution engine
- `backend/app/tasks/pipeline.py` — Celery async task
- `backend/app/api/routes/pipeline.py` — API routes
- `backend/app/schemas/pipeline.py` — Pydantic models
- `frontend/src/app/(dashboard)/pipeline/page.tsx` — main page
- `frontend/src/components/pipeline/PipelineCanvas.tsx` — React Flow canvas
- `frontend/src/components/pipeline/NodePalette.tsx` — draggable node list
- `frontend/src/components/pipeline/NodeConfig.tsx` — node config panel
