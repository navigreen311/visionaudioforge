"""Live capture WebSocket handler with per-frame analysis."""

from __future__ import annotations

import base64
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from app.ws.manager import manager


class CaptureWebSocket:
    """Handles a single capture WebSocket session."""

    def __init__(self) -> None:
        self._prev_frame: np.ndarray | None = None
        self._frame_counter: int = 0

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------
    async def handle_connection(
        self, websocket: WebSocket, session_id: str
    ) -> None:
        """Accept, stream frames, analyse, and return results."""
        channel = f"capture:{session_id}"
        await manager.connect(websocket, channel)
        try:
            while True:
                data = await websocket.receive_json()
                result = self._analyse_frame(data)
                await websocket.send_json(result)
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(websocket, channel)

    # ------------------------------------------------------------------
    # Frame analysis (runs synchronously — lightweight ops only)
    # ------------------------------------------------------------------
    def _analyse_frame(self, data: dict) -> dict:
        self._frame_counter += 1
        frame_b64: str = data.get("frame", "")

        # Decode base64 → numpy image
        raw = base64.b64decode(frame_b64)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if frame is None:
            return self._error_result("Could not decode frame")

        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))

        # Simple motion detection via absolute frame diff
        motion_detected = False
        if self._prev_frame is not None and self._prev_frame.shape == gray.shape:
            diff = cv2.absdiff(self._prev_frame, gray)
            motion_detected = bool(np.mean(diff) > 5.0)
        self._prev_frame = gray

        return {
            "frame_id": self._frame_counter,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis": {
                "brightness": round(brightness, 2),
                "motion_detected": motion_detected,
                "resolution": [w, h],
            },
            "detections": [],
        }

    @staticmethod
    def _error_result(msg: str) -> dict:
        return {
            "frame_id": -1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis": {
                "brightness": 0.0,
                "motion_detected": False,
                "resolution": [0, 0],
            },
            "detections": [],
            "error": msg,
        }
