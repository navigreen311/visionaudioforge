"""Capture API routes — RTSP, multi-cam, recording, snapshots."""

from __future__ import annotations

import os
import tempfile

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.capture.rtsp import RTSPStreamReader
from app.services.capture.recorder import ClipRecorder
from app.services.capture.multicam import multicam_manager

router = APIRouter(prefix="/api/capture", tags=["capture"])

# ---------------------------------------------------------------------------
# Singletons / state
# ---------------------------------------------------------------------------
_rtsp_readers: dict[str, RTSPStreamReader] = {}
_recorder = ClipRecorder(
    output_dir=os.environ.get("CAPTURE_OUTPUT_DIR", os.path.join(tempfile.gettempdir(), "vaf_captures"))
)


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
