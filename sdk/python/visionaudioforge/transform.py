"""Transform API wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .types import TransformResult

if TYPE_CHECKING:
    from .client import VAFClient


class TransformClient:
    """Wraps the /api/transform endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def apply(
        self,
        asset_id: str,
        operations: list[dict[str, Any]],
    ) -> TransformResult:
        """Apply a sequence of transformations to an asset."""
        resp = await self._client._request(
            "POST",
            "/api/transform/audio",
            json={"asset_id": asset_id, "operations": operations},
        )
        return TransformResult.model_validate(resp)

    async def list_operations(self) -> list[dict[str, Any]]:
        """List available transform operations."""
        resp = await self._client._request("GET", "/api/transform/presets")
        return resp if isinstance(resp, list) else resp.get("operations", [])

    async def get_result(self, transform_id: str) -> TransformResult:
        """Get the result of a transform job."""
        resp = await self._client._request(
            "GET", f"/api/transform/{transform_id}"
        )
        return TransformResult.model_validate(resp)
