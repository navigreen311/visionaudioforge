# Vision Preprocessing Service

## Overview

The vision preprocessing service provides image normalization, color-space conversion, edge detection, histogram equalization, and a configurable pipeline for chaining operations. It powers the `/api/vision/analyze` and `/api/vision/screen-analyze` endpoints.

## Architecture

```
backend/app/
├── services/vision/
│   ├── preprocessing.py   # ImagePreprocessor class
│   └── utils.py           # Encoding, decoding, stats, validation
├── schemas/vision.py      # Pydantic request/response models
└── api/routes/vision.py   # FastAPI route handlers
```

## Supported Operations

| Operation | Pipeline `op` | Parameters |
|---|---|---|
| Min-max normalize | `normalize` | `method: "min_max"`, `target_range: [0, 1]` |
| Z-score normalize | `normalize` | `method: "z_score"`, `global_stats: [mean, std]` (optional) |
| Per-channel normalize | `normalize` | `method: "per_channel"` |
| Color-space conversion | `color_space` | `from: "rgb"`, `to: "hsv"` (rgb, bgr, hsv, lab, gray) |
| Histogram equalization | `histogram_equalization` | _(none)_ |
| Edge detection | `edge_detection` | `method: "canny"|"sobel"|"laplacian"`, `low`, `high` |
| Resize | `resize` | `width`, `height`, `maintain_aspect: true` |

## API Reference

### POST `/api/vision/analyze`

Apply a sequence of preprocessing operations to an uploaded image.

**Request** (multipart form):
- `file` — image file (PNG, JPEG, etc.)
- `operations` — JSON string of operation steps

```json
[
  {"op": "normalize", "params": {"method": "min_max"}},
  {"op": "color_space", "params": {"from": "rgb", "to": "hsv"}}
]
```

**Response** (`200 OK`):
```json
{
  "image": "<base64-encoded PNG>",
  "stats": {
    "shape": [100, 100, 3],
    "dtype": "float32",
    "channels": [{"mean": 0.0, "std": 1.0, "min": -2.1, "max": 3.4}, ...]
  },
  "operations_applied": ["normalize", "color_space"],
  "processing_time_ms": 12.34
}
```

### POST `/api/vision/screen-analyze`

Analyze visual properties of a screenshot (brightness, edges, dominant colors).

**Request** (multipart form):
- `file` — screenshot image file

**Response** (`200 OK`):
```json
{
  "brightness": 127.5,
  "edge_density": 0.0342,
  "dominant_colors": [[255, 200, 100], [30, 30, 30], ...],
  "resolution": [1920, 1080]
}
```

## Usage Examples

### Python client

```python
import httpx

with open("photo.jpg", "rb") as f:
    resp = httpx.post(
        "http://localhost:8000/api/vision/analyze",
        files={"file": ("photo.jpg", f, "image/jpeg")},
        data={"operations": '[{"op": "normalize", "params": {"method": "min_max"}}]'},
    )

data = resp.json()
print(f"Processed in {data['processing_time_ms']} ms")
```

### curl

```bash
curl -X POST http://localhost:8000/api/vision/analyze \
  -F "file=@photo.jpg" \
  -F 'operations=[{"op":"normalize","params":{"method":"min_max"}}]'
```

## Running Tests

```bash
cd backend
python -m pytest tests/test_vision_preprocessing.py -v
```
