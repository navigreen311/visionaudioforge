"""Settings extra routes — integrations, API keys, and billing stubs."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
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


class ApiKeyCreate(BaseModel):
    label: str
    scopes: list[str] = Field(default_factory=lambda: ["read"])


class ApiKeyOut(BaseModel):
    id: str
    label: str
    prefix: str
    scopes: list[str]
    created_at: float


class BillingOverview(BaseModel):
    plan: str = "pro"
    seats_used: int = 3
    seats_total: int = 10
    current_period_start: str = "2026-03-01"
    current_period_end: str = "2026-03-31"
    monthly_cost_usd: float = 99.0
    usage_pct: float = 24.0


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

_api_keys: dict[str, dict[str, Any]] = {}


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


# ---------------------------------------------------------------------------
# Routes — API Keys
# ---------------------------------------------------------------------------

@router.get("/api-keys", response_model=list[ApiKeyOut])
async def list_api_keys():
    """List API keys (secrets masked)."""
    return list(_api_keys.values())


@router.post("/api-keys", response_model=ApiKeyOut)
async def create_api_key(body: ApiKeyCreate):
    """Create a new API key and return metadata (secret shown only once)."""
    kid = str(uuid.uuid4())
    key = ApiKeyOut(
        id=kid,
        label=body.label,
        prefix=f"vaf_{uuid.uuid4().hex[:8]}",
        scopes=body.scopes,
        created_at=time.time(),
    )
    _api_keys[kid] = key.model_dump()
    return key


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str):
    """Revoke an API key."""
    if key_id not in _api_keys:
        raise HTTPException(status_code=404, detail="API key not found")
    del _api_keys[key_id]
    return {"status": "revoked", "id": key_id}


# ---------------------------------------------------------------------------
# Routes — Billing
# ---------------------------------------------------------------------------

@router.get("/billing", response_model=BillingOverview)
async def get_billing():
    """Return billing / plan overview."""
    return BillingOverview()
