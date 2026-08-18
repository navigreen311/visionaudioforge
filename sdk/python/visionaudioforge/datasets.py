"""Dataset API wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .types import Dataset, DatasetVersion

if TYPE_CHECKING:
    from .client import VAFClient


class DatasetClient:
    """Wraps the /api/datasets endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def create(self, name: str, format: str = "parquet", metadata: dict[str, Any] | None = None) -> Dataset:
        """Create a new dataset."""
        payload: dict[str, Any] = {"name": name, "format": format}
        if metadata:
            payload["metadata"] = metadata
        resp = await self._client._request("POST", "/api/datasets", json=payload)
        return Dataset.model_validate(resp)

    async def list(self) -> list[Dataset]:
        """List all datasets."""
        resp = await self._client._request("GET", "/api/datasets")
        items = resp if isinstance(resp, list) else resp.get("datasets", [])
        return [Dataset.model_validate(d) for d in items]

    async def get(self, dataset_id: str) -> Dataset:
        """Get a dataset by ID."""
        resp = await self._client._request("GET", f"/api/datasets/{dataset_id}")
        return Dataset.model_validate(resp)

    async def delete(self, dataset_id: str) -> None:
        """Delete a dataset."""
        await self._client._request("DELETE", f"/api/datasets/{dataset_id}")

    async def create_version(self, dataset_id: str, version: str) -> DatasetVersion:
        """Create a new version of a dataset."""
        resp = await self._client._request(
            "POST",
            f"/api/datasets/{dataset_id}/versions",
            json={"version": version},
        )
        return DatasetVersion.model_validate(resp)

    async def list_versions(self, dataset_id: str) -> list[DatasetVersion]:
        """List all versions of a dataset."""
        resp = await self._client._request(
            "GET", f"/api/datasets/{dataset_id}/versions"
        )
        items = resp if isinstance(resp, list) else resp.get("versions", [])
        return [DatasetVersion.model_validate(v) for v in items]
