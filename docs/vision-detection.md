# Vision Detection, OCR & Error Analysis

## Overview

This module provides three computer-vision capabilities:

1. **Object Detection** — YOLOv8-based detection with bounding boxes, class labels, and confidence scores.
2. **OCR (Optical Character Recognition)** — Text extraction from images via Tesseract.
3. **Error Analysis** — Confusion matrix computation, per-class metrics, and systematic quality reporting for classification models.

All services degrade gracefully when optional dependencies (`ultralytics`, `pytesseract`) are not installed.

---

## Architecture

```
backend/app/services/vision/
├── __init__.py          # Public exports
├── detection.py         # ObjectDetector (YOLOv8)
├── ocr.py               # OCREngine (pytesseract)
└── error_analysis.py    # Confusion matrix & metrics

backend/app/api/routes/vision.py   # FastAPI endpoints
backend/tests/test_vision_detection.py
```

---

## API Endpoints

### POST `/api/vision/detect`

Detect objects in an uploaded image.

| Parameter    | Type   | Default | Description                     |
|-------------|--------|---------|----------------------------------|
| `file`       | file   | required| Image file (PNG, JPG, etc.)      |
| `confidence` | float  | 0.5     | Minimum confidence threshold     |
| `classes`    | string | null    | Comma-separated COCO class IDs  |

**Response:**
```json
{
  "detections": [
    {"bbox": [x1, y1, x2, y2], "class_id": 0, "class_name": "person", "confidence": 0.87}
  ],
  "count": 1,
  "visualization": "<base64-encoded PNG>",
  "processing_time_ms": 42.5
}
```

### POST `/api/vision/ocr`

Extract text from an uploaded image.

| Parameter | Type | Description          |
|-----------|------|----------------------|
| `file`    | file | Image file to process|

**Response:**
```json
{
  "full_text": "Hello World",
  "blocks": [{"text": "Hello", "bbox": [10, 20, 50, 15], "confidence": 92.5}],
  "processing_time_ms": 120.3
}
```

### POST `/api/vision/error-analysis`

Compute classification error analysis.

**Request body (JSON):**
```json
{
  "predictions": ["cat", "dog", "cat"],
  "ground_truth": ["cat", "cat", "cat"],
  "classes": ["cat", "dog"]
}
```

**Response:**
```json
{
  "confusion_matrix": [[2, 0], [1, 0]],
  "per_class": [{"class": "cat", "precision": 0.6667, "recall": 1.0, "f1": 0.8, "support": 2}],
  "overall": {"accuracy": 0.6667, "macro_precision": 0.3333, "macro_recall": 0.5, "macro_f1": 0.4},
  "top_confusions": [{"true_class": "dog", "predicted_class": "cat", "count": 1}],
  "total_samples": 3,
  "error_rate": 0.3333
}
```

---

## Services

### ObjectDetector

```python
from app.services.vision.detection import ObjectDetector

detector = ObjectDetector(model_name="yolov8n")
detections = detector.detect(image, confidence=0.5, classes=[0, 1])
batch_results = detector.detect_batch([img1, img2], confidence=0.3)
annotated = detector.draw_detections(image, detections)
```

- Model is lazy-loaded on first `detect()` call.
- Returns `[]` with a warning if `ultralytics` is not installed.

### OCREngine

```python
from app.services.vision.ocr import OCREngine

engine = OCREngine()
result = engine.extract_text(image)
# result["full_text"], result["blocks"], result["language"]
```

- Returns `{"error": "OCR engine not installed"}` if `pytesseract` is unavailable.

### Error Analysis Functions

```python
from app.services.vision.error_analysis import generate_quality_report

report = generate_quality_report(y_true, y_pred, class_names)
```

Individual functions: `compute_confusion_matrix`, `class_level_metrics`, `overall_metrics`, `identify_top_confusions`.

---

## Optional Dependencies

| Package        | Purpose           | Install                      |
|---------------|-------------------|------------------------------|
| `ultralytics` | YOLOv8 detection  | `pip install ultralytics`    |
| `pytesseract` | OCR text extraction| `pip install pytesseract`   |
| `opencv-python`| Image I/O (required)| `pip install opencv-python`|
| `numpy`       | Array ops (required)| `pip install numpy`         |

---

## Running Tests

```bash
cd backend
pytest tests/test_vision_detection.py -v
```

---

## Environment Variables

No additional environment variables are required. Tesseract binary path can be configured via `pytesseract.pytesseract.tesseract_cmd` if needed.
