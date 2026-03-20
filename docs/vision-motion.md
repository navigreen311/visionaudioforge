# Vision Motion Analysis

Optical flow and frame differencing services for motion detection and visualization.

## Overview

This module provides two families of motion analysis:

1. **Optical Flow** -- estimates per-pixel or per-feature motion vectors between consecutive frames.
2. **Frame Differencing** -- detects regions of change using absolute difference and thresholding.

## Architecture

```
POST /api/vision/optical-flow
POST /api/vision/frame-diff
        |
        v
  vision.py (routes)
        |
        v
  MotionAnalyzer           (backend/app/services/vision/motion.py)
  visualization helpers     (backend/app/services/vision/visualization.py)
```

## API Endpoints

### POST `/api/vision/optical-flow`

Accepts two image uploads and computes optical flow.

**Parameters:**
| Name   | Type       | Description                         |
|--------|------------|-------------------------------------|
| frame1 | UploadFile | First frame (PNG/JPG)               |
| frame2 | UploadFile | Second frame (PNG/JPG)              |
| method | query str  | `lucas-kanade` (default) or `farneback` |

**Response:**
```json
{
  "method": "lucas-kanade",
  "stats": {
    "mean_magnitude": 12.5,
    "max_magnitude": 42.1,
    "motion_area_pct": 8.3,
    "dominant_direction_deg": 45.0
  },
  "visualization": "<base64 PNG>",
  "processing_time_ms": 23.4
}
```

### POST `/api/vision/frame-diff`

Accepts two or three image uploads and computes frame differencing.

**Parameters:**
| Name      | Type       | Description                              |
|-----------|------------|------------------------------------------|
| frame1    | UploadFile | First frame                              |
| frame2    | UploadFile | Second frame                             |
| frame3    | UploadFile | Third frame (required for `three-frame`) |
| method    | query str  | `consecutive` (default) or `three-frame` |
| threshold | query int  | Pixel difference threshold (0-255, default 25) |

**Response:**
```json
{
  "method": "consecutive",
  "motion_percentage": 5.23,
  "motion_mask": "<base64 PNG>",
  "stats": { ... },
  "processing_time_ms": 11.2
}
```

## Algorithms

### Lucas-Kanade (Sparse)
Tracks up to 100 corner features using pyramidal Lucas-Kanade. Good for tracking distinct objects with texture.

### Farneback (Dense)
Computes per-pixel flow using polynomial expansion. Produces a full motion field but is more expensive.

### Consecutive Frame Differencing
`absdiff` + threshold + morphological opening. Fast, simple, but sensitive to noise and lighting changes.

### Three-Frame Differencing
AND of two consecutive diffs. Reduces false positives from lighting changes and produces cleaner motion masks.

## Running Tests

```bash
cd backend
python -m pytest tests/test_vision_motion.py -v
```

## Environment Variables

No additional environment variables required. Uses OpenCV (bundled with `opencv-python-headless`).
