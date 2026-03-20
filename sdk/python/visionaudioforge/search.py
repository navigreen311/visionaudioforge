"""Search API wrapper."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from .types import IndexResult, SearchResult

if TYPE_CHECKING:
    from .client import VAFClient


class SearchClient:
    """Wraps the /api/v1/search endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def query(
        self,
        text: str | None = None,
        image_path: str | None = None,
        k: int = 10,
    ) -> list[SearchResult]:
        """Run a multimodal search query (text, image, or both)."""
        if image_path:
            files = {"file": ("image", Path(image_path).read_bytes())}
            data: dict[str, Any] = {"k": str(k)}
            if text:
                data["text"] = text
            resp = await self._client._request(
                "POST", "/api/v1/search/query", files=files, data=data
            )
        else:
            resp = await self._client._request(
                "POST", "/api/v1/search/query", json={"text": text, "k": k}
            )
        items = resp if isinstance(resp, list) else resp.get("results", [])
        return [SearchResult.model_validate(r) for r in items]

    async def index(self, asset_id: str) -> IndexResult:
        """Index an asset for search."""
        resp = await self._client._request(
            "POST", "/api/v1/search/index", json={"asset_id": asset_id}
        )
        return IndexResult.model_validate(resp)

    async def similar(self, asset_id: str, k: int = 10) -> list[SearchResult]:
        """Find assets similar to a given asset."""
        resp = await self._client._request(
            "GET",
            f"/api/v1/search/similar/{asset_id}",
            params={"k": k},
        )
        items = resp if isinstance(resp, list) else resp.get("results", [])
        return [SearchResult.model_validate(r) for r in items]
