"""RTSP stream reader with auto-reconnection."""

from __future__ import annotations

import asyncio
import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class RTSPStreamReader:
    """Connect to and read frames from an RTSP camera stream."""

    MAX_FAILURES = 3
    BACKOFF_BASE = 1.0  # seconds

    def __init__(self, rtsp_url: str) -> None:
        self.rtsp_url = rtsp_url
        self._cap: cv2.VideoCapture | None = None
        self._consecutive_failures = 0

    async def connect(self) -> bool:
        """Open the RTSP stream. Returns True on success."""
        loop = asyncio.get_event_loop()
        self._cap = await loop.run_in_executor(
            None, cv2.VideoCapture, self.rtsp_url
        )
        opened = self._cap.isOpened()
        if opened:
            self._consecutive_failures = 0
            logger.info("RTSP connected: %s", self.rtsp_url)
        else:
            logger.warning("RTSP failed to open: %s", self.rtsp_url)
        return opened

    async def read_frame(self) -> np.ndarray | None:
        """Read the next frame. Auto-reconnects after repeated failures."""
        if self._cap is None or not self._cap.isOpened():
            return None

        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, self._cap.read)

        if ret:
            self._consecutive_failures = 0
            return frame

        self._consecutive_failures += 1
        logger.warning(
            "RTSP read failure %d/%d",
            self._consecutive_failures,
            self.MAX_FAILURES,
        )

        if self._consecutive_failures >= self.MAX_FAILURES:
            logger.info("Attempting RTSP reconnection with backoff...")
            await self.disconnect()
            backoff = self.BACKOFF_BASE * self._consecutive_failures
            await asyncio.sleep(backoff)
            success = await self.connect()
            if not success:
                logger.error("RTSP reconnection failed: %s", self.rtsp_url)
        return None

    async def get_stream_info(self) -> dict:
        """Return metadata about the current RTSP stream."""
        if self._cap is None or not self._cap.isOpened():
            return {"url": self.rtsp_url, "width": 0, "height": 0, "fps": 0.0, "codec": ""}

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self._cap.get(cv2.CAP_PROP_FPS)
        fourcc_int = int(self._cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join(chr((fourcc_int >> (8 * i)) & 0xFF) for i in range(4))

        return {
            "url": self.rtsp_url,
            "width": width,
            "height": height,
            "fps": round(fps, 2),
            "codec": codec,
        }

    async def disconnect(self) -> None:
        """Release the underlying VideoCapture."""
        if self._cap is not None:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._cap.release)
            self._cap = None
            logger.info("RTSP disconnected: %s", self.rtsp_url)
