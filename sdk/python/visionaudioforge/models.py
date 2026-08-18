"""Model lifecycle API wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .types import Comparison, Experiment, Model, TrainingJob

if TYPE_CHECKING:
    from .client import VAFClient


class ModelClient:
    """Wraps the /api/registry endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def register(
        self,
        name: str,
        version: str,
        backbone: str,
        metrics: dict[str, Any] | None = None,
    ) -> Model:
        """Register a new model."""
        payload: dict[str, Any] = {
            "name": name,
            "version": version,
            "backbone": backbone,
        }
        if metrics:
            payload["metrics"] = metrics
        resp = await self._client._request("POST", "/api/registry/models", json=payload)
        return Model.model_validate(resp)

    async def list(self, status: str | None = None) -> list[Model]:
        """List registered models, optionally filtered by status."""
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        resp = await self._client._request("GET", "/api/registry/models", params=params)
        items = resp if isinstance(resp, list) else resp.get("models", [])
        return [Model.model_validate(m) for m in items]

    async def promote(self, model_id: str, status: str) -> Model:
        """Promote a model to a new status (e.g., staging, production)."""
        resp = await self._client._request(
            "PUT", f"/api/registry/models/{model_id}/status", json={"status": status}
        )
        return Model.model_validate(resp)

    async def compare(self, model_a_id: str, model_b_id: str) -> Comparison:
        """Compare metrics between two models."""
        # POST, not GET: the registry defines comparison as a POST endpoint.
        resp = await self._client._request(
            "POST",
            "/api/registry/compare",
            json={"model_a": model_a_id, "model_b": model_b_id},
        )
        return Comparison.model_validate(resp)

    async def start_training(self, config: dict[str, Any]) -> TrainingJob:
        """Start a training job."""
        resp = await self._client._request("POST", "/api/experiments", json=config)
        return TrainingJob.model_validate(resp)

    async def get_experiment(self, exp_id: str) -> Experiment:
        """Retrieve an experiment by ID."""
        resp = await self._client._request("GET", f"/api/experiments/{exp_id}")
        return Experiment.model_validate(resp)
