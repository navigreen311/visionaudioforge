"""Settings extra routes — workspace integration configs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.settings import WorkspaceIntegration

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


def _serialise(row: WorkspaceIntegration) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "type": row.type,
        "enabled": row.enabled,
        "config": row.config or {},
        "connected_at": row.connected_at.isoformat() if row.connected_at else "",
    }


# ---------------------------------------------------------------------------
# Routes — Integrations
# ---------------------------------------------------------------------------

@router.get("/integrations", response_model=list[IntegrationConfig])
async def list_integrations(
    workspace_id: UUID | None = Query(
        None, description="Scope the list to one workspace"
    ),
    db: AsyncSession = Depends(get_async_session),
):
    """List configured integrations.

    Previously this returned two hardcoded entries — a Slack channel and an S3
    bucket that were never configured by anyone — which made an empty
    integration list look populated.
    """
    stmt = select(WorkspaceIntegration)
    if workspace_id is not None:
        stmt = stmt.where(WorkspaceIntegration.workspace_id == workspace_id)
    stmt = stmt.order_by(WorkspaceIntegration.connected_at)

    rows = (await db.execute(stmt)).scalars().all()
    return [_serialise(r) for r in rows]


@router.post("/integrations", response_model=IntegrationConfig)
async def add_integration(
    body: IntegrationConfig,
    workspace_id: UUID | None = Query(
        None, description="Workspace the integration belongs to"
    ),
    db: AsyncSession = Depends(get_async_session),
):
    """Add a new integration."""
    row = WorkspaceIntegration(
        workspace_id=workspace_id,
        name=body.name,
        type=body.type,
        enabled=body.enabled,
        config=body.config or {},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _serialise(row)


# NOTE: /api/settings/api-keys is served by routes/settings_api_keys.py (DB-backed)
# and /api/settings/billing by routes/settings_billing.py, whose response shape
# matches the console's BillingTab. The in-memory stubs that used to live here
# shadowed both and were removed when those routers were mounted.
