"""Settings extra routes — workspace integration configs."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/settings", tags=["settings-extra"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class IntegrationConfig(BaseModel):
    id: str = ""
    name: str = ""
    type: str = ""
    enabled: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    connected_at: str = ""


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_integrations: list[dict[str, Any]] = [
    IntegrationConfig(
        id="int-1", name="Slack", type="messaging", enabled=True,
        config={"channel": "#alerts"}, connected_at="2026-01-10T12:00:00Z",
    ).model_dump(),
    IntegrationConfig(
        id="int-2", name="S3 Bucket", type="storage", enabled=True,
        config={"bucket": "vaf-assets"}, connected_at="2026-02-05T08:00:00Z",
    ).model_dump(),
]


# ---------------------------------------------------------------------------
# Routes — Integrations
# ---------------------------------------------------------------------------

@router.get("/integrations", response_model=list[IntegrationConfig])
async def list_integrations():
    """List configured integrations."""
    return _integrations


@router.post("/integrations", response_model=IntegrationConfig)
async def add_integration(body: IntegrationConfig):
    """Add a new integration."""
    body.id = f"int-{uuid.uuid4().hex[:6]}"
    entry = body.model_dump()
    _integrations.append(entry)
    return entry


# NOTE: /api/settings/api-keys is served by routes/settings_api_keys.py (DB-backed)
# and /api/settings/billing by routes/settings_billing.py, whose response shape
# matches the console's BillingTab. The in-memory stubs that used to live here
# shadowed both and were removed when those routers were mounted.
