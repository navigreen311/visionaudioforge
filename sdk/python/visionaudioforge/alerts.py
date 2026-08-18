"""Alerts API wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .types import Alert

if TYPE_CHECKING:
    from .client import VAFClient


class AlertClient:
    """Wraps the /api/alerts endpoints."""

    def __init__(self, client: VAFClient) -> None:
        self._client = client

    async def create(self, type: str, message: str, severity: str = "info") -> Alert:
        """Create a new alert."""
        resp = await self._client._request(
            "POST",
            "/api/alerts",
            json={"type": type, "message": message, "severity": severity},
        )
        return Alert.model_validate(resp)

    async def list(self, severity: str | None = None) -> list[Alert]:
        """List alerts, optionally filtered by severity."""
        params: dict[str, Any] = {}
        if severity:
            params["severity"] = severity
        resp = await self._client._request("GET", "/api/alerts", params=params)
        items = resp if isinstance(resp, list) else resp.get("alerts", [])
        return [Alert.model_validate(a) for a in items]

    async def get(self, alert_id: str) -> Alert:
        """Get an alert by ID."""
        resp = await self._client._request("GET", f"/api/alerts/{alert_id}")
        return Alert.model_validate(resp)

    async def dismiss(self, alert_id: str) -> None:
        """Dismiss an alert."""
        await self._client._request("DELETE", f"/api/alerts/{alert_id}")
