"""Vision API routes: detection, OCR, error analysis, and stubs."""

from __future__ import annotations

import base64
import json
import logging
import time

import cv2
import numpy as np
from fastapi import APIRouter, File, Form, Query, UploadFile
from pydantic import BaseModel
from starlette.responses import JSONResponse

from app.services.vision.detection import ObjectDetector
from app.services.vision.error_analysis import generate_quality_report
from app.services.vision.motion import MotionAnalyzer
from app.services.vision.ocr import OCREngine
from app.services.vision.preprocessing import ImagePreprocessor
from app.services.vision.screen_intel import ScreenIntelligence
from app.services.vision.depth import DepthEstimator
from app.services.vision.anomaly import AnomalyDetector
from app.services.vision.face_plate import FacePlateDetector
from app.services.vision.tracking import MultiObjectTracker, TrajectoryAnalyzer
from app.services.vision.segmentation import SegmentationService
from app.services.vision.pose import PoseEstimator
from app.services.vision.embedding_viz import EmbeddingVisualizer

router = APIRouter(prefix="/api/vision", tags=["vision"])

# Shared service singletons (lazy-loaded internally)
_detector = ObjectDetector()
_ocr_engine = OCREngine()
_segmentation = SegmentationService()
_pose_estimator = PoseEstimator()
_trajectory_analyzer = TrajectoryAnalyzer()
_embedding_viz = EmbeddingVisualizer()
_preprocessor = ImagePreprocessor()
_motion_analyzer = MotionAnalyzer()
_screen_intel = ScreenIntelligence()
_depth_estimator = DepthEstimator()
_anomaly_detector = AnomalyDetector()
_face_plate = FacePlateDetector()

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------


async def _decode_upload(file: UploadFile, flags: int = cv2.IMREAD_COLOR) -> np.ndarray | None:
    """Read an UploadFile and decode it into an OpenCV image."""
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    return cv2.imdecode(nparr, flags)


# ------------------------------------------------------------------
# Image preprocessing / analyze
# ------------------------------------------------------------------


@router.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    operations: str = Form("[]", description="JSON array of pipeline steps"),
):
    """Apply preprocessing operations to an uploaded image.

    Accepts a file and a JSON string of operations (list of
    ``{"op": "<name>", "params": {…}}`` dicts).  Returns the
    processed image as base64 PNG together with statistics.
    """
    t0 = time.perf_counter()

    try:
        steps = json.loads(operations)
        if not isinstance(steps, list):
            return JSONResponse(status_code=400, content={"error": "operations must be a JSON array"})
    except json.JSONDecodeError as exc:
        return JSONResponse(status_code=400, content={"error": f"Invalid operations JSON: {exc}"})

    image = await _decode_upload(file)
    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    try:
        if steps:
            result = _preprocessor.preprocess_pipeline(image, steps)
        else:
            result = image.copy()
    except (ValueError, KeyError) as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Preprocessing failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})

    # Encode result to base64 PNG (handle float images)
    out = result
    if out.dtype != np.uint8:
        out = np.clip(out * 255 if out.max() <= 1.0 else out, 0, 255).astype(np.uint8)

    _, buf = cv2.imencode(".png", out)
    image_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "image": image_b64,
        "original_shape": list(image.shape),
        "result_shape": list(result.shape),
        "operations_applied": len(steps),
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# Optical flow
# ------------------------------------------------------------------


@router.post("/optical-flow")
async def optical_flow(
    frame1: UploadFile = File(...),
    frame2: UploadFile = File(...),
    method: str = Query("lucas_kanade", description="lucas_kanade or farneback"),
):
    """Compute optical flow between two consecutive frames."""
    t0 = time.perf_counter()

    img1 = await _decode_upload(frame1)
    img2 = await _decode_upload(frame2)
    if img1 is None or img2 is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file(s)"})

    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    try:
        if method == "farneback":
            result = _motion_analyzer.farneback_dense(gray1, gray2)
            # Create HSV flow visualization
            hsv = np.zeros((*gray1.shape, 3), dtype=np.uint8)
            hsv[..., 1] = 255
            mag = result["magnitude"]
            ang = result["angle"]
            hsv[..., 0] = (ang * 180 / np.pi / 2).astype(np.uint8)
            hsv[..., 2] = cv2.normalize(mag, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            vis = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
            _, buf = cv2.imencode(".png", vis)
            vis_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

            stats = _motion_analyzer.compute_motion_stats(result)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "method": "farneback",
                "mean_magnitude": result["mean_magnitude"],
                "max_magnitude": result["max_magnitude"],
                "stats": stats,
                "visualization": vis_b64,
                "processing_time_ms": round(elapsed_ms, 2),
            }
        else:
            result = _motion_analyzer.lucas_kanade(gray1, gray2)
            stats = _motion_analyzer.compute_motion_stats(result)

            # Visualization: draw arrows on frame1
            from app.services.vision.visualization import draw_optical_flow_arrows
            tracked = result["tracked_points"]
            vis = draw_optical_flow_arrows(img1, tracked["old"], tracked["new"])
            _, buf = cv2.imencode(".png", vis)
            vis_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "method": "lucas_kanade",
                "num_tracked": result["num_tracked"],
                "mean_magnitude": result["mean_magnitude"],
                "stats": stats,
                "visualization": vis_b64,
                "processing_time_ms": round(elapsed_ms, 2),
            }
    except Exception as exc:
        logger.exception("Optical flow computation failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})


# ------------------------------------------------------------------
# Frame differencing
# ------------------------------------------------------------------


@router.post("/frame-diff")
async def frame_diff(
    files: list[UploadFile] = File(...),
    threshold: int = Query(25, ge=0, le=255, description="Binarization threshold"),
):
    """Compute frame differencing for motion detection.

    Upload 2 frames for consecutive diff or 3 frames for three-frame diff.
    """
    t0 = time.perf_counter()

    if len(files) < 2 or len(files) > 3:
        return JSONResponse(
            status_code=400,
            content={"error": "Upload exactly 2 or 3 frames"},
        )

    frames = []
    for f in files:
        img = await _decode_upload(f)
        if img is None:
            return JSONResponse(status_code=400, content={"error": f"Invalid image: {f.filename}"})
        frames.append(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))

    try:
        if len(frames) == 2:
            result = _motion_analyzer.frame_diff_consecutive(frames[0], frames[1], threshold=threshold)
            diff_method = "consecutive"
        else:
            result = _motion_analyzer.frame_diff_three_frame(frames[0], frames[1], frames[2], threshold=threshold)
            diff_method = "three_frame"
    except Exception as exc:
        logger.exception("Frame differencing failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})

    # Encode motion mask
    _, buf = cv2.imencode(".png", result["motion_mask"])
    mask_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "method": diff_method,
        "motion_percentage": round(result["motion_percentage"], 4),
        "motion_mask": mask_b64,
        "threshold": threshold,
        "num_frames": len(frames),
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# Screen analysis
# ------------------------------------------------------------------


@router.post("/screen-analyze")
async def screen_analyze(file: UploadFile = File(...)):
    """Analyze a screenshot for UI elements, layout, brightness, and text."""
    t0 = time.perf_counter()

    image = await _decode_upload(file)
    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    try:
        result = _screen_intel.analyze_screenshot(image)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Screen analysis failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "brightness": result["brightness"],
        "edge_density": result["edge_density"],
        "dominant_colors": result["dominant_colors"],
        "ui_elements": result["ui_elements"],
        "text_content": result["text_content"],
        "layout_type": result["layout_type"],
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# Object detection
# ------------------------------------------------------------------


@router.post("/detect")
async def detect(
    file: UploadFile = File(...),
    confidence: float = Query(0.5, ge=0.0, le=1.0),
    iou_threshold: float = Query(0.45, ge=0.0, le=1.0, description="IoU threshold for NMS"),
    max_detections: int = Query(100, ge=1, le=1000, description="Maximum detections to return"),
    classes: str | None = Query(None, description="Comma-separated class IDs"),
):
    """Detect objects in an uploaded image.

    Accepts multipart file upload with confidence, iou_threshold, and
    max_detections parameters.  Returns detections list, annotated image
    as base64 PNG, and processing time.
    """
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

    # Apply IoU-based NMS filtering when detections are available
    if detections and iou_threshold < 1.0:
        boxes = np.array([d["bbox"] for d in detections], dtype=np.float32)
        scores = np.array([d["confidence"] for d in detections], dtype=np.float32)
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(), scores.tolist(), confidence, iou_threshold
        )
        if len(indices) > 0:
            kept = indices.flatten().tolist()
            detections = [detections[i] for i in kept]

    # Cap to max_detections
    detections = detections[:max_detections]

    # Generate annotated visualization
    annotated = _detector.draw_detections(image, detections)
    _, buf = cv2.imencode(".png", annotated)
    image_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "detections": detections,
        "count": len(detections),
        "image_b64": image_b64,
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# OCR
# ------------------------------------------------------------------


@router.post("/ocr")
async def ocr(
    file: UploadFile = File(...),
    language: str = Query("en", description="OCR language code (e.g. en, de, fr)"),
    output_format: str = Query("text", description="Output format: text or json"),
    confidence_filter: float = Query(0.0, ge=0.0, le=1.0, description="Min confidence to include a word"),
):
    """Extract text from an uploaded image using OCR.

    Accepts multipart file upload with language, output_format, and
    confidence_filter parameters.  Returns extracted text, word-level
    details, detected language, and overall confidence.
    """
    t0 = time.perf_counter()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    result = _ocr_engine.extract_text(image)

    # Build word-level output from blocks
    blocks = result.get("blocks", [])
    words = []
    total_conf = 0.0
    for block in blocks:
        conf = block.get("confidence", 0.0)
        # Tesseract returns confidence in 0-100 range; normalise to 0-1
        conf_normalised = conf / 100.0 if conf > 1.0 else conf
        if conf_normalised >= confidence_filter:
            words.append({
                "text": block["text"],
                "bbox": block["bbox"],
                "confidence": round(conf_normalised, 4),
            })
            total_conf += conf_normalised

    overall_confidence = round(total_conf / len(words), 4) if words else 0.0
    detected_language = result.get("language", language)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "text": result["full_text"],
        "words": words,
        "language": detected_language,
        "confidence": overall_confidence,
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


# ------------------------------------------------------------------
# Panoptic segmentation
# ------------------------------------------------------------------


@router.post("/panoptic")
async def panoptic(file: UploadFile = File(...)):
    """Perform panoptic segmentation on an uploaded image.

    Combines semantic (stuff) and instance (thing) segmentation into a
    single unified result.
    """
    t0 = time.perf_counter()

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    # Get detections for instance segmentation
    detections = _detector.detect(image, confidence=0.3)
    result = _segmentation.panoptic_segmentation(image, detections)

    # Encode combined mask as base64 PNG
    _, buf = cv2.imencode(".png", result["combined_mask"])
    combined_b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

    # Serialize thing masks
    things = []
    for thing in result["thing_masks"]:
        things.append({
            "instance_id": thing["instance_id"],
            "class": thing["class"],
            "bbox": thing["bbox"],
            "area": thing["area"],
        })

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    return {
        "things": things,
        "num_stuff_pixels": int(np.sum(result["stuff_mask"])),
        "num_things": len(things),
        "class_map": result["class_map"],
        "combined_mask": combined_b64,
        "processing_time_ms": round(elapsed_ms, 2),
    }


# ------------------------------------------------------------------
# Trajectory analysis
# ------------------------------------------------------------------


class TrajectoryRequest(BaseModel):
    track_history: list[list[float]]


@router.post("/trajectory")
async def trajectory(body: TrajectoryRequest):
    """Analyze a track trajectory for movement patterns."""
    analysis = _trajectory_analyzer.analyze_trajectory(body.track_history)
    return analysis


# ------------------------------------------------------------------
# Embedding visualization
# ------------------------------------------------------------------


class EmbeddingVisualizeRequest(BaseModel):
    embeddings: list[list[float]]
    labels: list | None = None
    method: str = "tsne"


@router.post("/embeddings/visualize")
async def embeddings_visualize(body: EmbeddingVisualizeRequest):
    """Reduce and visualize embeddings as a scatter plot.

    Returns a base64-encoded PNG scatter plot.
    """
    embeddings = np.array(body.embeddings, dtype=np.float64)
    reduced = _embedding_viz.reduce_dimensions(embeddings, method=body.method)
    plot_b64 = _embedding_viz.plot_embeddings(reduced, labels=body.labels)

    return {
        "plot": plot_b64,
        "method": body.method,
        "num_points": len(body.embeddings),
    }


# ------------------------------------------------------------------
# Specialized analysis — depth, anomaly, faces, plates, screen intel
#
# The services behind these were implemented and unit-tested but never
# mounted, so the only way to reach them was to import the service directly.
# ------------------------------------------------------------------


def _png_b64(image: np.ndarray) -> str:
    """Encode a BGR image as base64 PNG for JSON transport."""
    _, buf = cv2.imencode(".png", image)
    return base64.b64encode(buf.tobytes()).decode("utf-8")


@router.post("/depth")
async def estimate_depth(file: UploadFile = File(...)):
    """Estimate relative depth from a single image."""
    t0 = time.perf_counter()

    image = await _decode_upload(file)
    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    try:
        result = _depth_estimator.estimate_depth(image)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Depth estimation failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})

    depth_map = result["depth_map"]
    return {
        "min_depth": result["min_depth"],
        "max_depth": result["max_depth"],
        # The map itself is large; return its shape and a colourised preview
        # rather than several megabytes of float32 in JSON.
        "depth_map_shape": list(depth_map.shape),
        "visualization": _png_b64(result["visualization"]),
        "method": "relative",
        "processing_time_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


@router.post("/anomaly")
async def detect_anomaly(file: UploadFile = File(...)):
    """Flag an image as anomalous against baseline image statistics."""
    t0 = time.perf_counter()

    image = await _decode_upload(file)
    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    try:
        result = _anomaly_detector.detect_anomaly(image)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Anomaly detection failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})

    return {
        "is_anomaly": result["is_anomaly"],
        "anomaly_score": result["anomaly_score"],
        "anomaly_regions": result["anomaly_regions"],
        "reason": result["reason"],
        "processing_time_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


@router.post("/faces")
async def detect_faces(file: UploadFile = File(...)):
    """Detect faces and return an annotated preview."""
    t0 = time.perf_counter()

    image = await _decode_upload(file)
    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    try:
        faces = _face_plate.detect_faces(image)
        annotated = _face_plate.draw_detections(image, faces)
    except Exception as exc:
        logger.exception("Face detection failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})

    return {
        "faces": faces,
        "count": len(faces),
        "visualization": _png_b64(annotated),
        "processing_time_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


@router.post("/plates")
async def detect_plates(file: UploadFile = File(...)):
    """Detect license plates and return an annotated preview."""
    t0 = time.perf_counter()

    image = await _decode_upload(file)
    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    try:
        plates = _face_plate.detect_license_plates(image)
        annotated = _face_plate.draw_detections(image, plates)
    except Exception as exc:
        logger.exception("Plate detection failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})

    return {
        "plates": plates,
        "count": len(plates),
        "visualization": _png_b64(annotated),
        "processing_time_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


@router.post("/screen-intel")
async def screen_intel(file: UploadFile = File(...)):
    """Analyse a screenshot for UI elements, layout and colour."""
    t0 = time.perf_counter()

    image = await _decode_upload(file)
    if image is None:
        return JSONResponse(status_code=400, content={"error": "Invalid image file"})

    try:
        result = _screen_intel.analyze_screenshot(image)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:
        logger.exception("Screen analysis failed")
        return JSONResponse(status_code=500, content={"error": f"Processing error: {exc}"})

    return {
        "ui_elements": result["ui_elements"],
        "text_content": result["text_content"],
        "brightness": result["brightness"],
        "edge_density": result["edge_density"],
        "dominant_colors": result["dominant_colors"],
        "layout_type": result["layout_type"],
        "processing_time_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }
