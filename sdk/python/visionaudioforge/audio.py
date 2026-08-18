"""Audio API wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .types import AudioAnalysis, Classification, DiarizationResult, Transcript

if TYPE_CHECKING:
    from .client import VAFClient


class AudioClient:
    """Wraps the /api/audio endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def analyze(
        self, audio_path: str, operations: list[str] | None = None
    ) -> AudioAnalysis:
        """Analyze an audio file."""
        ops = operations or ["all"]
        files = {"file": ("audio", Path(audio_path).read_bytes())}
        data: dict[str, Any] = {"operations": ",".join(ops)}
        resp = await self._client._request("POST", "/api/audio/analyze", files=files, data=data)
        return AudioAnalysis.model_validate(resp)

    async def augment(self, audio_path: str, config: dict[str, Any]) -> bytes:
        """Augment an audio file and return raw bytes."""
        files = {"file": ("audio", Path(audio_path).read_bytes())}
        # Send config as JSON string in form data
        import json

        data: dict[str, Any] = {"config": json.dumps(config)}
        # Use raw httpx for binary response
        headers: dict[str, str] = {}
        if self._client.token:
            headers["Authorization"] = f"Bearer {self._client.token}"
        elif self._client.api_key:
            headers["X-API-Key"] = self._client.api_key
        response = await self._client._http.post(
            "/api/audio/augment", files=files, data=data, headers=headers
        )
        response.raise_for_status()
        return response.content

    async def transcribe(self, audio_path: str) -> Transcript:
        """Transcribe speech from an audio file."""
        files = {"file": ("audio", Path(audio_path).read_bytes())}
        resp = await self._client._request("POST", "/api/audio/transcribe", files=files)
        return Transcript.model_validate(resp)

    async def diarize(self, audio_path: str) -> DiarizationResult:
        """Perform speaker diarization on an audio file."""
        files = {"file": ("audio", Path(audio_path).read_bytes())}
        resp = await self._client._request("POST", "/api/audio/diarize", files=files)
        return DiarizationResult.model_validate(resp)

    async def classify(self, audio_path: str) -> Classification:
        """Classify the content of an audio file."""
        files = {"file": ("audio", Path(audio_path).read_bytes())}
        resp = await self._client._request("POST", "/api/audio/classify", files=files)
        return Classification.model_validate(resp)
