"""Developer Tools routes — OpenAPI spec, proto files, node templates, SDK info."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/developer", tags=["developer"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NodeTemplateCreate(BaseModel):
    name: str
    node_type: str
    description: str = ""
    default_config: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_templates: list[dict] = []


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


@router.post("/node-templates")
async def create_node_template(body: NodeTemplateCreate) -> dict[str, Any]:
    """Create a pipeline node template."""
    template = {
        "id": f"tmpl-{len(_templates) + 1:04d}",
        "name": body.name,
        "node_type": body.node_type,
        "description": body.description,
        "default_config": body.default_config or {},
    }
    _templates.append(template)
    return template


@router.get("/node-templates")
async def list_node_templates() -> list[dict]:
    """List all node templates."""
    return _templates


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
async def developer_health() -> dict[str, Any]:
    """Developer tools health check."""
    return {
        "api_version": "1.0.0",
        "openapi_available": True,
        "grpc_available": True,
        "sdks_available": ["python", "javascript"],
        "templates_count": len(_templates),
    }
