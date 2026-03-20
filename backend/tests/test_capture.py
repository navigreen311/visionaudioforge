"""Tests for the live capture engine — M1."""

import base64
import json

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from app.main import app
from app.ws.manager import ConnectionManager
from app.services.capture.manager import CaptureSessionManager
from app.ws.capture import CaptureWebSocket


# ---------------------------------------------------------------
# ConnectionManager tests
# ---------------------------------------------------------------

class TestConnectionManager:
    def setup_method(self):
        self.mgr = ConnectionManager()

    @pytest.mark.anyio
    async def test_connect_and_disconnect(self):
        """Connections tracked per-channel; disconnect cleans up."""

        class FakeWS:
            accepted = False
            async def accept(self):
                self.accepted = True
            async def send_json(self, data):
                pass

        ws = FakeWS()
        await self.mgr.connect(ws, "ch1")
        assert ws.accepted
        assert self.mgr.get_connection_count("ch1") == 1
        assert self.mgr.get_connection_count() == 1

        self.mgr.disconnect(ws, "ch1")
        assert self.mgr.get_connection_count("ch1") == 0
        assert self.mgr.get_connection_count() == 0

    @pytest.mark.anyio
    async def test_broadcast(self):
        """Broadcast delivers message to all channel connections."""

        messages_received: list[dict] = []

        class FakeWS:
            async def accept(self):
                pass
            async def send_json(self, data):
                messages_received.append(data)

        ws1, ws2 = FakeWS(), FakeWS()
        await self.mgr.connect(ws1, "ch")
        await self.mgr.connect(ws2, "ch")

        await self.mgr.broadcast("ch", {"hello": "world"})
        assert len(messages_received) == 2
        assert all(m == {"hello": "world"} for m in messages_received)

    @pytest.mark.anyio
    async def test_channel_isolation(self):
        """Connections in different channels are independent."""

        class FakeWS:
            async def accept(self):
                pass

        ws1, ws2 = FakeWS(), FakeWS()
        await self.mgr.connect(ws1, "a")
        await self.mgr.connect(ws2, "b")

        assert self.mgr.get_connection_count("a") == 1
        assert self.mgr.get_connection_count("b") == 1
        assert self.mgr.get_connection_count() == 2


# ---------------------------------------------------------------
# CaptureSessionManager tests
# ---------------------------------------------------------------

class TestCaptureSessionManager:
    def setup_method(self):
        self.mgr = CaptureSessionManager()

    def test_create_session(self):
        result = self.mgr.create_session("ws-1", "camera")
        assert "session_id" in result
        assert result["source_type"] == "camera"
        assert "created_at" in result

    def test_end_session(self):
        created = self.mgr.create_session("ws-1", "screen")
        sid = created["session_id"]
        self.mgr.increment_frames(sid)
        self.mgr.increment_frames(sid)

        ended = self.mgr.end_session(sid)
        assert ended["session_id"] == sid
        assert ended["frames_processed"] == 2
        assert ended["duration_s"] >= 0

    def test_end_session_not_found(self):
        with pytest.raises(ValueError):
            self.mgr.end_session("nonexistent")

    def test_list_active_sessions(self):
        self.mgr.create_session("ws-1", "camera")
        self.mgr.create_session("ws-1", "screen")
        self.mgr.create_session("ws-2", "camera")

        active = self.mgr.list_active_sessions("ws-1")
        assert len(active) == 2

    def test_ended_session_not_in_active(self):
        created = self.mgr.create_session("ws-1", "camera")
        self.mgr.end_session(created["session_id"])
        active = self.mgr.list_active_sessions("ws-1")
        assert len(active) == 0


# ---------------------------------------------------------------
# CaptureWebSocket frame analysis test
# ---------------------------------------------------------------

class TestWebSocketFrameProcessing:
    def test_analyse_frame(self):
        """Verify frame decode, brightness, and motion detection."""
        handler = CaptureWebSocket()

        # Create a 100x100 gray image and encode to base64 JPEG
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        import cv2

        _, buf = cv2.imencode(".jpg", img)
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

        result = handler._analyse_frame({"frame": b64})

        assert result["frame_id"] == 1
        assert result["analysis"]["resolution"] == [100, 100]
        assert 100 < result["analysis"]["brightness"] < 160  # ~128
        assert result["analysis"]["motion_detected"] is False

        # Second identical frame → no motion
        result2 = handler._analyse_frame({"frame": b64})
        assert result2["analysis"]["motion_detected"] is False

        # Third frame with very different content → motion
        bright_img = np.full((100, 100, 3), 255, dtype=np.uint8)
        _, buf2 = cv2.imencode(".jpg", bright_img)
        b64_bright = base64.b64encode(buf2.tobytes()).decode("utf-8")
        result3 = handler._analyse_frame({"frame": b64_bright})
        assert result3["analysis"]["motion_detected"] is True


# ---------------------------------------------------------------
# WebSocket integration test
# ---------------------------------------------------------------

class TestWebSocketRoute:
    def test_websocket_endpoint_connects(self):
        """Verify /ws/live/stream/{session_id} accepts connections."""
        client = TestClient(app)
        img = np.full((50, 50, 3), 100, dtype=np.uint8)
        import cv2

        _, buf = cv2.imencode(".jpg", img)
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")

        with client.websocket_connect("/ws/live/stream/test-session-1") as ws:
            ws.send_json({"frame": b64})
            data = ws.receive_json()
            assert data["frame_id"] == 1
            assert "analysis" in data
            assert data["analysis"]["resolution"] == [50, 50]
