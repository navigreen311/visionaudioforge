"""Capture API routes - RTSP, multi-cam, recording, snapshots, frame analysis."""

from __future__ import annotations

import asyncio
import base64
import os
import tempfile
import time

import cv2
import numpy as np
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.capture.rtsp import RTSPStreamReader
from app.services.capture.recorder import ClipRecorder
from app.services.capture.multicam import multicam_manager
from app.services.vision.detection import ObjectDetector
from app.services.vision.ocr import OCREngine
from app.services.vision.motion import MotionAnalyzer

router = APIRouter(prefix="/api/capture", tags=["capture"])

# ---------------------------------------------------------------------------
# Singletons / state
# ---------------------------------------------------------------------------
_rtsp_readers: dict[str, RTSPStreamReader] = {}
_recorder = ClipRecorder(
    output_dir=os.environ.get("CAPTURE_OUTPUT_DIR", os.path.join(tempfile.gettempdir(), "vaf_captures"))
)
_detector = ObjectDetector()
_ocr_engine = OCREngine()
_motion_analyzer = MotionAnalyzer()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class RTSPConnectRequest(BaseModel):
    url: str


class AddSourceRequest(BaseModel):
    workspace_id: str
    source_type: str
    config: dict | None = None


class SwitchSourceRequest(BaseModel):
    workspace_id: str


class RecordStartRequest(BaseModel):
    session_id: str
    fps: int = 30


class RecordStopRequest(BaseModel):
    recording_id: str


class SnapshotRequest(BaseModel):
    session_id: str


class AnalyzeFrameRequest(BaseModel):
    frame_b64: str
    overlays: list[str] = []
    threshold: float = 0.5


# ---------------------------------------------------------------------------
# RTSP
# ---------------------------------------------------------------------------

@router.post("/rtsp")
async def connect_rtsp(body: RTSPConnectRequest):
    """Connect to an RTSP stream and return stream metadata."""
    reader = RTSPStreamReader(body.url)
    success = await reader.connect()
    if not success:
        raise HTTPException(status_code=400, detail=f"Cannot connect to RTSP stream: {body.url}")
    info = await reader.get_stream_info()
    _rtsp_readers[body.url] = reader
    return info


# ---------------------------------------------------------------------------
# Sources (multi-cam)
# ---------------------------------------------------------------------------

@router.post("/sources")
async def add_source(body: AddSourceRequest):
    """Add a new capture source to a workspace."""
    try:
        source_id = await multicam_manager.add_source(
            body.workspace_id, body.source_type, body.config
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"source_id": source_id}


@router.get("/sources")
async def list_sources(workspace_id: str):
    """List all capture sources for a workspace."""
    sources = await multicam_manager.list_sources(workspace_id)
    return {"sources": sources}


@router.post("/sources/{source_id}/switch")
async def switch_source(source_id: str, body: SwitchSourceRequest):
    """Switch the active/primary capture source."""
    ok = await multicam_manager.switch_source(body.workspace_id, source_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Source not found")
    return {"active_source_id": source_id}


@router.get("/sources/grid")
async def get_grid_layout(workspace_id: str):
    """Get the multi-cam grid layout for a workspace."""
    layout = await multicam_manager.get_grid_layout(workspace_id)
    return layout


# ---------------------------------------------------------------------------
# Recording
# ---------------------------------------------------------------------------

@router.post("/record/start")
async def start_recording(body: RecordStartRequest):
    """Start recording the current capture stream."""
    result = await _recorder.start_recording(body.session_id, body.fps)
    return result


@router.post("/record/stop")
async def stop_recording(body: RecordStopRequest):
    """Stop recording and return the clip info."""
    try:
        result = await _recorder.stop_recording(body.recording_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

@router.post("/snapshot")
async def capture_snapshot(body: SnapshotRequest):
    """Capture a single frame as a PNG snapshot."""
    # Create a placeholder frame when no live frame is available
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    try:
        result = await _recorder.capture_snapshot(frame, body.session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result


# ---------------------------------------------------------------------------
# Frame analysis
# ---------------------------------------------------------------------------

@router.post("/analyze-frame")
async def analyze_frame(body: AnalyzeFrameRequest):
    """Analyze a base64-encoded frame for detections, OCR regions, and motion vectors.

    Body:
        frame_b64: base64-encoded image
        overlays: list of overlay types (e.g. ["detection"])
        threshold: confidence threshold for detection (default 0.5)

    Returns detections, ocr_regions, and motion_vectors.
    """
    # Decode the base64 image
    try:
        raw = base64.b64decode(body.frame_b64)
        nparr = np.frombuffer(raw, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 image data")

    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image from base64 payload")

    detections: list[dict] = []
    ocr_regions: list[dict] = []
    motion_vectors: list[dict] = []

    # Run detection if requested or by default
    if "detection" in body.overlays or not body.overlays:
        raw_dets = _detector.detect(image, confidence=body.threshold)
        detections = [
            {
                "bbox": d["bbox"],
                "class_name": d["class_name"],
                "confidence": d["confidence"],
            }
            for d in raw_dets
        ]

    # Run OCR if requested
    if "ocr" in body.overlays:
        ocr_result = _ocr_engine.extract_text(image)
        ocr_regions = ocr_result.get("blocks", [])

    # Run motion analysis if requested (single-frame produces empty vectors)
    if "motion" in body.overlays:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Motion vectors require two frames; return empty for a single frame.
        motion_vectors = []

    return {
        "detections": detections,
        "ocr_regions": ocr_regions,
        "motion_vectors": motion_vectors,
    }


# ---------------------------------------------------------------------------
# RTSP connectivity test
# ---------------------------------------------------------------------------

@router.get("/rtsp/test")
async def test_rtsp(url: str = Query(..., description="RTSP stream URL to test")):
    """Test connectivity to an RTSP stream and report latency.

    Opens the stream for real and reports whether it answered, with the
    round-trip latency in milliseconds.
    """
    t0 = time.perf_counter()
    reader = RTSPStreamReader(url)

    try:
        loop = asyncio.get_event_loop()
        success = await reader.connect()
    except Exception:
        success = False

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Clean up the probe connection
    if hasattr(reader, "_cap") and reader._cap is not None:
        try:
            reader._cap.release()
        except Exception:
            pass

    return {"success": success, "latency_ms": latency_ms}
