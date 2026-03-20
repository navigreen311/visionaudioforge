"""Vision API routes: detection, OCR, error analysis, and stubs."""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np
from fastapi import APIRouter, File, Query, UploadFile
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.services.vision.detection import ObjectDetector
from app.services.vision.error_analysis import generate_quality_report
from app.services.vision.ocr import OCREngine
from app.services.vision.tracking import MultiObjectTracker
from app.services.vision.segmentation import SegmentationService
from app.services.vision.pose import PoseEstimator

router = APIRouter(prefix="/api/vision", tags=["vision"])

# Shared service singletons (lazy-loaded internally)
_detector = ObjectDetector()
_ocr_engine = OCREngine()
_segmentation = SegmentationService()
_pose_estimator = PoseEstimator()


# ------------------------------------------------------------------
# Existing stub endpoints (preserved)
# ------------------------------------------------------------------


@router.post("/analyze")
async def analyze():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/optical-flow")
async def optical_flow():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/frame-diff")
async def frame_diff():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


@router.post("/screen-analyze")
async def screen_analyze():
    return JSONResponse(status_code=501, content={"status": "not_implemented", "module": "vision"})


# ------------------------------------------------------------------
# Object detection
# ------------------------------------------------------------------


@router.post("/detect")
async def detect(
    file: UploadFile = File(...),
    confidence: float = Query(0.5, ge=0.0, le=1.0),
    classes: str | None = Query(None, description="Comma-separated class IDs"),
):
    """Detect objects in an uploaded image."""
    t0 = time.perf_counter()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    class_ids = None
    if classes:
        class_ids = [int(c.strip()) for c in classes.split(",") if c.strip().isdigit()]

    detections = _detector.detect(image, confidence=confidence, classes=class_ids or None)

    # Generate annotated visualization
    annotated = _detector.draw_detections(image, detections)
    _, buf = cv2.imencode(".png", annotated)
    visualization = base64.b64encode(buf.tobytes()).decode("utf-8")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "detections": detections,
        "count": len(detections),
        "visualization": visualization,
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# OCR
# ------------------------------------------------------------------


@router.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    """Extract text from an uploaded image using OCR."""
    t0 = time.perf_counter()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    result = _ocr_engine.extract_text(image)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "full_text": result["full_text"],
        "blocks": result.get("blocks", []),
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# Error analysis
# ------------------------------------------------------------------


class ErrorAnalysisRequest(BaseModel):
    predictions: list[str]
    ground_truth: list[str]
    classes: list[str]


@router.post("/error-analysis")
async def error_analysis(body: ErrorAnalysisRequest):
    """Compute classification error analysis from predictions vs ground truth."""
    if len(body.predictions) != len(body.ground_truth):
        return JSONResponse(
            status_code=400,
            content={"error": "predictions and ground_truth must have the same length"},
        )

    report = generate_quality_report(body.ground_truth, body.predictions, body.classes)
    return report


# ------------------------------------------------------------------
# Multi-object tracking
# ------------------------------------------------------------------


@router.post("/track")
async def track(
    files: list[UploadFile] = File(...),
    method: str = Query("sort", description="Tracking method: sort or centroid"),
):
    """Track objects across a sequence of frames.

    Upload multiple image files representing consecutive video frames.
    Returns tracked objects with trajectories.
    """
    t0 = time.perf_counter()

    tracker = MultiObjectTracker(method=method)
    all_frame_results: list[list[dict]] = []

    for frame_file in files:
        contents = await frame_file.read()
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            continue

        # Run detection on each frame
        detections = _detector.detect(image, confidence=0.3)
        tracked = tracker.update(detections)

        # Convert to JSON-serializable format
        frame_tracks = []
        for t in tracked:
            frame_tracks.append({
                "track_id": t["track_id"],
                "bbox": t["bbox"],
                "class_name": t["class_name"],
                "confidence": t["confidence"],
                "age": t["age"],
                "centroid": t["centroid"],
            })
        all_frame_results.append(frame_tracks)

    trajectories = tracker.get_trajectories()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "frames": all_frame_results,
        "trajectories": {str(k): v for k, v in trajectories.items()},
        "total_frames": len(all_frame_results),
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# Segmentation
# ------------------------------------------------------------------


@router.post("/segment")
async def segment(
    file: UploadFile = File(...),
    method: str = Query("semantic", description="Segmentation method: semantic or instance"),
):
    """Segment objects in an image.

    Returns masks and an overlay visualization.
    """
    t0 = time.perf_counter()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    if method == "instance":
        detections = _detector.detect(image, confidence=0.3)
        instances = _segmentation.instance_segmentation(image, detections)
        masks = [inst["mask"] for inst in instances]
        overlay = _segmentation.mask_overlay(image, masks)
        mask_images = _segmentation.export_masks(masks)

        _, buf = cv2.imencode(".png", overlay)
        overlay_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

        result_instances = []
        for inst, mask_b64 in zip(instances, mask_images):
            result_instances.append({
                "class": inst["class"],
                "bbox": inst["bbox"],
                "area": inst["area"],
                "mask_image": mask_b64,
            })

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "method": "instance",
            "instances": result_instances,
            "overlay": overlay_b64,
            "processing_time_ms": round(elapsed_ms, 2),
        }
    else:
        result = _segmentation.semantic_segmentation(image)
        mask = result["mask"]
        overlay = _segmentation.mask_overlay(image, [mask])
        mask_images = _segmentation.export_masks([mask])

        _, buf = cv2.imencode(".png", overlay)
        overlay_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "method": "semantic",
            "classes": result["classes"],
            "class_colors": result["class_colors"],
            "mask_image": mask_images[0],
            "overlay": overlay_b64,
            "processing_time_ms": round(elapsed_ms, 2),
        }


# ------------------------------------------------------------------
# Pose estimation
# ------------------------------------------------------------------


@router.post("/pose")
async def pose(file: UploadFile = File(...)):
    """Estimate human pose keypoints in an uploaded image.

    Returns keypoints and a skeleton visualization.
    """
    t0 = time.perf_counter()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    poses = _pose_estimator.estimate(image)

    # Generate skeleton visualization
    skeleton_img = _pose_estimator.draw_skeleton(image, poses)
    _, buf = cv2.imencode(".png", skeleton_img)
    visualization = base64.b64encode(buf.tobytes()).decode("utf-8")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Serialize poses (keypoints are already dicts)
    serialized_poses = []
    for p in poses:
        serialized_poses.append({
            "keypoints": p["keypoints"],
            "bbox": p["bbox"],
            "score": p["score"],
        })

    return {
        "poses": serialized_poses,
        "count": len(poses),
        "visualization": visualization,
        "processing_time_ms": round(elapsed_ms, 2),
    }
