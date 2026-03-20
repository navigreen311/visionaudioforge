"""Tests for capture enhancements — RTSP, recorder, multi-cam, API routes."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.capture.rtsp import RTSPStreamReader
from app.services.capture.recorder import ClipRecorder
from app.services.capture.multicam import MultiCamManager


# ---------------------------------------------------------------
# RTSPStreamReader tests
# ---------------------------------------------------------------

class TestRTSPStreamReader:
    @pytest.mark.anyio
    async def test_rtsp_connect_invalid_url(self):
        """An invalid/unreachable RTSP URL should return False from connect()."""
        reader = RTSPStreamReader("rtsp://invalid-host:554/nonexistent")
        result = await reader.connect()
        assert result is False

    @pytest.mark.anyio
    async def test_rtsp_get_stream_info_not_connected(self):
        """Stream info on a disconnected reader returns zero values."""
        reader = RTSPStreamReader("rtsp://fake:554/stream")
        info = await reader.get_stream_info()
        assert info["url"] == "rtsp://fake:554/stream"
        assert info["width"] == 0
        assert info["height"] == 0

    @pytest.mark.anyio
    async def test_rtsp_read_frame_not_connected(self):
        """read_frame returns None when not connected."""
        reader = RTSPStreamReader("rtsp://fake:554/stream")
        frame = await reader.read_frame()
        assert frame is None

    @pytest.mark.anyio
    async def test_rtsp_disconnect_safe(self):
        """disconnect on a never-connected reader should not raise."""
        reader = RTSPStreamReader("rtsp://fake:554/stream")
        await reader.disconnect()  # should not raise


# ---------------------------------------------------------------
# ClipRecorder tests
# ---------------------------------------------------------------

class TestClipRecorder:
    @pytest.mark.anyio
    async def test_clip_recorder_start_stop(self):
        """Start a recording, add frames, stop, and verify output file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = ClipRecorder(output_dir=tmpdir)
            result = await recorder.start_recording("session-1", fps=10)
            recording_id = result["recording_id"]
            assert "started_at" in result

            # Add frames
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            for _ in range(5):
                await recorder.add_frame(recording_id, frame)

            # Check status
            status = await recorder.get_recording_status(recording_id)
            assert status["is_recording"] is True
            assert status["frames_captured"] == 5

            # Stop
            clip = await recorder.stop_recording(recording_id)
            assert clip["frames"] == 5
            assert clip["duration_s"] == 0.5  # 5 frames / 10 fps
            assert clip["size_bytes"] > 0
            assert os.path.exists(clip["path"])

    @pytest.mark.anyio
    async def test_snapshot_saves_frame(self):
        """capture_snapshot writes a PNG file to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = ClipRecorder(output_dir=tmpdir)
            frame = np.full((50, 50, 3), 200, dtype=np.uint8)
            result = await recorder.capture_snapshot(frame, "snap-session")
            assert os.path.exists(result["path"])
            assert result["path"].endswith(".png")
            assert "timestamp" in result

            # Verify the saved image dimensions
            saved = cv2.imread(result["path"])
            assert saved.shape[:2] == (50, 50)

    @pytest.mark.anyio
    async def test_stop_nonexistent_recording_raises(self):
        """Stopping a non-existent recording raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = ClipRecorder(output_dir=tmpdir)
            with pytest.raises(ValueError):
                await recorder.stop_recording("nonexistent-id")


# ---------------------------------------------------------------
# MultiCamManager tests
# ---------------------------------------------------------------

class TestMultiCamManager:
    @pytest.mark.anyio
    async def test_multicam_add_remove_source(self):
        """Add a source, verify it's listed, then remove it."""
        mgr = MultiCamManager()
        source_id = await mgr.add_source("ws-1", "webcam", {"device": 0})
        assert source_id is not None

        sources = await mgr.list_sources("ws-1")
        assert len(sources) == 1
        assert sources[0]["source_type"] == "webcam"
        assert sources[0]["is_primary"] is True

        removed = await mgr.remove_source(source_id)
        assert removed is True

        sources = await mgr.list_sources("ws-1")
        assert len(sources) == 0

    @pytest.mark.anyio
    async def test_multicam_switch_source(self):
        """Switching active source updates primary correctly."""
        mgr = MultiCamManager()
        s1 = await mgr.add_source("ws-1", "webcam")
        s2 = await mgr.add_source("ws-1", "screen")

        active = await mgr.get_active_source("ws-1")
        assert active is not None
        assert active["source_id"] == s1

        ok = await mgr.switch_source("ws-1", s2)
        assert ok is True
        active = await mgr.get_active_source("ws-1")
        assert active is not None
        assert active["source_id"] == s2

    @pytest.mark.anyio
    async def test_multicam_invalid_source_type(self):
        """Invalid source type raises ValueError."""
        mgr = MultiCamManager()
        with pytest.raises(ValueError, match="Invalid source_type"):
            await mgr.add_source("ws-1", "invalid_type")

    @pytest.mark.anyio
    async def test_multicam_grid_layout(self):
        """Grid layout adapts to number of sources."""
        mgr = MultiCamManager()
        layout = await mgr.get_grid_layout("ws-empty")
        assert layout["layout"] == "1x1"

        await mgr.add_source("ws-grid", "webcam")
        await mgr.add_source("ws-grid", "screen")
        await mgr.add_source("ws-grid", "rtsp")
        layout = await mgr.get_grid_layout("ws-grid")
        assert layout["layout"] == "2x2"
        assert layout["source_count"] == 3


# ---------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------

class TestCaptureAPI:
    @pytest.mark.anyio
    async def test_api_sources_endpoint(self):
        """POST /api/capture/sources and GET /api/capture/sources work."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # Add a source
            resp = await ac.post(
                "/api/capture/sources",
                json={
                    "workspace_id": "test-ws",
                    "source_type": "webcam",
                    "config": {},
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "source_id" in data

            # List sources
            resp = await ac.get(
                "/api/capture/sources",
                params={"workspace_id": "test-ws"},
            )
            assert resp.status_code == 200
            sources = resp.json()["sources"]
            assert len(sources) >= 1

    @pytest.mark.anyio
    async def test_api_rtsp_invalid(self):
        """POST /api/capture/rtsp with invalid URL returns 400."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/capture/rtsp",
                json={"url": "rtsp://invalid:554/fake"},
            )
            assert resp.status_code == 400

    @pytest.mark.anyio
    async def test_api_record_start_stop(self):
        """POST record/start and record/stop lifecycle."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            start_resp = await ac.post(
                "/api/capture/record/start",
                json={"session_id": "test-session", "fps": 10},
            )
            assert start_resp.status_code == 200
            rid = start_resp.json()["recording_id"]

            stop_resp = await ac.post(
                "/api/capture/record/stop",
                json={"recording_id": rid},
            )
            assert stop_resp.status_code == 200

    @pytest.mark.anyio
    async def test_api_snapshot(self):
        """POST /api/capture/snapshot returns snapshot info."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/capture/snapshot",
                json={"session_id": "snap-test"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "path" in data
            assert "timestamp" in data
