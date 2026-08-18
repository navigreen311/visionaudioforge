"""Vision API wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .types import AnalysisResult, Detection, FlowResult, OCRResult, SegmentationResult, TrackingResult

if TYPE_CHECKING:
    from .client import VAFClient


class VisionClient:
    """Wraps the /api/vision endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def analyze(self, image_path: str, operations: list[str]) -> AnalysisResult:
        """Run one or more vision operations on an image."""
        files = {"file": ("image", Path(image_path).read_bytes())}
        data: dict[str, Any] = {"operations": ",".join(operations)}
        resp = await self._client._request("POST", "/api/vision/analyze", files=files, data=data)
        return AnalysisResult.model_validate(resp)

    async def detect(self, image_path: str, confidence: float = 0.5) -> list[Detection]:
        """Run object detection on an image."""
        files = {"file": ("image", Path(image_path).read_bytes())}
        data: dict[str, Any] = {"confidence": str(confidence)}
        resp = await self._client._request("POST", "/api/vision/detect", files=files, data=data)
        items = resp if isinstance(resp, list) else resp.get("detections", [])
        return [Detection.model_validate(d) for d in items]

    async def optical_flow(
        self, frame1_path: str, frame2_path: str, method: str = "farneback"
    ) -> FlowResult:
        """Compute optical flow between two frames."""
        files = {
            "frame1": ("frame1", Path(frame1_path).read_bytes()),
            "frame2": ("frame2", Path(frame2_path).read_bytes()),
        }
        data: dict[str, Any] = {"method": method}
        resp = await self._client._request("POST", "/api/vision/optical-flow", files=files, data=data)
        return FlowResult.model_validate(resp)

    async def ocr(self, image_path: str) -> OCRResult:
        """Extract text from an image."""
        files = {"file": ("image", Path(image_path).read_bytes())}
        resp = await self._client._request("POST", "/api/vision/ocr", files=files)
        return OCRResult.model_validate(resp)

    async def segment(self, image_path: str) -> SegmentationResult:
        """Segment an image into regions."""
        files = {"file": ("image", Path(image_path).read_bytes())}
        resp = await self._client._request("POST", "/api/vision/segment", files=files)
        return SegmentationResult.model_validate(resp)

    async def track(self, frame_paths: list[str]) -> TrackingResult:
        """Track objects across a sequence of frames."""
        files = [
            ("frames", (f"frame_{i}", Path(p).read_bytes()))
            for i, p in enumerate(frame_paths)
        ]
        resp = await self._client._request("POST", "/api/vision/track", files=files)
        return TrackingResult.model_validate(resp)
