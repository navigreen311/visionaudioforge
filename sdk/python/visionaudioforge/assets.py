"""Assets API wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .types import Asset

if TYPE_CHECKING:
    from .client import VAFClient


class AssetClient:
    """Wraps the /api/assets endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def upload(self, file_path: str, metadata: dict[str, Any] | None = None) -> Asset:
        """Upload a file as an asset."""
        import json

        files = {"file": (Path(file_path).name, Path(file_path).read_bytes())}
        data: dict[str, Any] = {}
        if metadata:
            data["metadata"] = json.dumps(metadata)
        resp = await self._client._request(
            "POST", "/api/assets", files=files, data=data
        )
        return Asset.model_validate(resp)

    async def list(self, type: str | None = None) -> list[Asset]:
        """List assets, optionally filtered by type."""
        params: dict[str, Any] = {}
        if type:
            params["type"] = type
        resp = await self._client._request("GET", "/api/assets", params=params)
        items = resp if isinstance(resp, list) else resp.get("assets", [])
        return [Asset.model_validate(a) for a in items]

    async def get(self, asset_id: str) -> Asset:
        """Get an asset by ID."""
        resp = await self._client._request("GET", f"/api/assets/{asset_id}")
        return Asset.model_validate(resp)

    async def delete(self, asset_id: str) -> None:
        """Delete an asset."""
        await self._client._request("DELETE", f"/api/assets/{asset_id}")

    async def download(self, asset_id: str) -> bytes:
        """Download an asset's file content."""
        headers: dict[str, str] = {}
        if self._client.token:
            headers["Authorization"] = f"Bearer {self._client.token}"
        elif self._client.api_key:
            headers["X-API-Key"] = self._client.api_key
        response = await self._client._http.get(
            f"/api/assets/{asset_id}/download", headers=headers
        )
        response.raise_for_status()
        return response.content
