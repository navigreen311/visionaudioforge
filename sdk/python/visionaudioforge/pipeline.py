"""Pipeline API wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .types import Pipeline, PipelineRun

if TYPE_CHECKING:
    from .client import VAFClient


class PipelineClient:
    """Wraps the /api/v1/pipelines endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def create(self, name: str, definition: dict[str, Any]) -> Pipeline:
        """Create a new pipeline."""
        resp = await self._client._request(
            "POST",
            "/api/v1/pipelines",
            json={"name": name, "definition": definition},
        )
        return Pipeline.model_validate(resp)

    async def run(self, pipeline_id: str) -> PipelineRun:
        """Execute a pipeline."""
        resp = await self._client._request(
            "POST", f"/api/v1/pipelines/{pipeline_id}/run"
        )
        return PipelineRun.model_validate(resp)

    async def list(self) -> list[Pipeline]:
        """List all pipelines."""
        resp = await self._client._request("GET", "/api/v1/pipelines")
        items = resp if isinstance(resp, list) else resp.get("pipelines", [])
        return [Pipeline.model_validate(p) for p in items]

    async def generate_from_description(self, description: str) -> Pipeline:
        """Generate a pipeline definition from a natural-language description."""
        resp = await self._client._request(
            "POST",
            "/api/v1/pipelines/generate",
            json={"description": description},
        )
        return Pipeline.model_validate(resp)
