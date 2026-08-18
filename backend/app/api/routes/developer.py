"""Developer Tools routes — OpenAPI spec, proto files, node templates, SDK info."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.plugin import CustomNode

router = APIRouter(prefix="/api/developer", tags=["developer"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NodeTemplateCreate(BaseModel):
    name: str
    node_type: str
    description: str = ""
    default_config: dict[str, Any] | None = None


def _serialise_template(node: CustomNode) -> dict[str, Any]:
    """Render a stored custom node in the node-template shape."""
    return {
        "id": str(node.id),
        "name": node.name,
        "node_type": node.category,
        "description": node.description,
        "default_config": node.node_metadata or {},
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/openapi")
async def get_openapi_spec(request: Request) -> dict[str, Any]:
    """Get the full OpenAPI specification."""
    return request.app.openapi()


@router.get("/proto")
async def get_proto_file() -> dict[str, Any]:
    """Get the gRPC proto file definition."""
    return {
        "filename": "visionaudioforge.proto",
        "syntax": "proto3",
        "services": [
            "VisionService",
            "AudioService",
            "ModelRegistryService",
            "PipelineService",
            "SearchService",
        ],
        "download_url": "/api/developer/proto/download",
    }


@router.get("/proto/download")
async def download_proto() -> dict[str, str]:
    """Download proto file content."""
    proto = '''syntax = "proto3";

package visionaudioforge.v1;

service VisionService {
  rpc Analyze (AnalyzeRequest) returns (AnalyzeResponse);
  rpc Detect (DetectRequest) returns (DetectResponse);
}

service AudioService {
  rpc Analyze (AudioAnalyzeRequest) returns (AudioAnalyzeResponse);
}

service ModelRegistryService {
  rpc Register (RegisterRequest) returns (ModelResponse);
  rpc ListModels (ListRequest) returns (ModelListResponse);
}
'''
    return {"content": proto, "content_type": "text/x-protobuf"}


@router.post("/node-templates", status_code=201)
async def create_node_template(
    body: NodeTemplateCreate,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Create a pipeline node template.

    Stored as a custom_nodes row: a pipeline referencing a template whose
    definition disappeared on restart cannot run.
    """
    node = CustomNode(
        workspace_id=uuid.UUID(str(workspace_id)) if workspace_id else None,
        name=body.name,
        category=body.node_type,
        description=body.description,
        node_metadata=body.default_config or {},
        status="template",
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return _serialise_template(node)


@router.get("/node-templates")
async def list_node_templates(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List all node templates."""
    stmt = select(CustomNode).where(CustomNode.status == "template")
    if workspace_id:
        stmt = stmt.where(CustomNode.workspace_id == uuid.UUID(str(workspace_id)))
    rows = (await db.execute(stmt.order_by(CustomNode.created_at))).scalars().all()
    return [_serialise_template(n) for n in rows]


@router.get("/sdks")
async def list_sdks() -> list[dict]:
    """List available SDKs."""
    return [
        {
            "language": "python",
            "package": "visionaudioforge",
            "version": "1.0.0",
            "install": "pip install visionaudioforge",
            "docs_url": "/docs/sdk/python",
        },
        {
            "language": "javascript",
            "package": "@visionaudioforge/sdk",
            "version": "1.0.0",
            "install": "npm install @visionaudioforge/sdk",
            "docs_url": "/docs/sdk/javascript",
        },
    ]


@router.get("/health")
async def developer_health(
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Developer tools health check."""
    templates_count = (
        await db.execute(
            select(func.count())
            .select_from(CustomNode)
            .where(CustomNode.status == "template")
        )
    ).scalar() or 0

    return {
        "api_version": "1.0.0",
        "openapi_available": True,
        "grpc_available": True,
        "sdks_available": ["python", "javascript"],
        "templates_count": templates_count,
    }
