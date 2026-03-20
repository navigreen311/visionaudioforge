# Video / Vision Transform Studio

## Overview

The Video Transform Studio provides image and video frame manipulation tools
accessible through both a REST API and an interactive frontend UI. All
transforms run on the server using OpenCV — no GPU or heavy model downloads
are required for V1.

## Architecture

```
Frontend (Next.js)               Backend (FastAPI)
┌────────────────────┐           ┌──────────────────────────────────┐
│ TransformPage      │  POST     │ /api/transform/video/*           │
│  - upload zone     │ ───────>  │   routes/transform.py            │
│  - mode selector   │  JSON     │        │                         │
│  - BeforeAfter     │ <───────  │   VideoTransformService          │
│    Slider          │           │   services/transform/            │
└────────────────────┘           │     video_transform.py           │
                                 └──────────────────────────────────┘
```

## Capabilities

| Feature             | Method / Endpoint                          | Notes                              |
|---------------------|--------------------------------------------|-------------------------------------|
| Background Removal  | `POST /api/transform/video/background-remove` | threshold, grabcut, rembg (opt.)  |
| Super Resolution    | `POST /api/transform/video/super-resolution`  | 2x / 4x via INTER_CUBIC          |
| Style Transfer      | `POST /api/transform/video/style`             | sketch, edges, cartoon, oil       |
| Auto Crop           | `POST /api/transform/video/auto-crop`         | 16:9, 4:3, 1:1, 9:16             |
| Thumbnail           | `POST /api/transform/video/thumbnail`         | middle, brightest, first          |
| Scene Detection     | service-level only (V1)                       | histogram-based cut detection     |
| Stabilisation       | service-level only (V1)                       | Farneback optical-flow alignment  |

## API Reference

### Background Remove

```
POST /api/transform/video/background-remove
Content-Type: multipart/form-data

file:   <image>          (required)
method: threshold|grabcut (default: threshold)

Response 200:
{
  "image":              "<base64 PNG, RGBA>",
  "method":             "threshold",
  "processing_time_ms": 42.5
}
```

### Super Resolution

```
POST /api/transform/video/super-resolution
Content-Type: multipart/form-data

file:  <image>   (required)
scale: 2|4       (default: 2)

Response 200:
{
  "image":              "<base64 PNG>",
  "original_size":      [100, 100],
  "output_size":        [200, 200],
  "scale":              2,
  "processing_time_ms": 15.3
}
```

### Style Transfer

```
POST /api/transform/video/style
Content-Type: multipart/form-data

file:  <image>                            (required)
style: sketch|edges|cartoon|oil_painting  (default: sketch)

Response 200:
{
  "image":              "<base64 PNG>",
  "style":              "sketch",
  "processing_time_ms": 28.1
}
```

### Auto Crop

```
POST /api/transform/video/auto-crop
Content-Type: multipart/form-data

file:   <image>                (required)
aspect: 16:9|4:3|1:1|9:16     (default: 16:9)

Response 200:
{
  "image":         "<base64 PNG>",
  "original_size": [200, 200],
  "cropped_size":  [200, 112]
}
```

### Thumbnail

```
POST /api/transform/video/thumbnail
Content-Type: multipart/form-data

files:  <image[]>                  (required, multiple)
method: middle|brightest|first     (default: middle)

Response 200:
{
  "thumbnail":   "<base64 PNG>",
  "frame_index": 5
}
```

## Environment Variables

No additional environment variables are required for V1. All transforms use
OpenCV which is already in the project dependencies.

Optional: install `rembg` for neural-network background removal:

```bash
pip install rembg
```

## Running Tests

```bash
cd backend
python -m pytest tests/test_video_transform.py -v
```

## Frontend Usage

1. Navigate to the **Transform** page from the sidebar.
2. Select the **Video / Image** tab.
3. Choose a transform mode (Background Remove, Super Resolution, etc.).
4. Upload an image and configure options.
5. Click **Transform** and review the before/after comparison.
6. Download the result.

## V2 Roadmap

- ESRGAN / Real-ESRGAN for true super-resolution
- Video file upload with automatic frame extraction
- Batch processing and Celery task queue integration
- Scene detection + thumbnail endpoints exposed via API
- Frame stabilisation endpoint for video clips
