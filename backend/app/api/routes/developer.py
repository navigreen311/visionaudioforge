"""Developer API routes — documentation, custom nodes, and gRPC proto access."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, PlainTextResponse

from app.grpc.server import PROTO_PATH
from app.services.plugins.api_docs import APIDocGenerator
from app.services.plugins.node_sdk import CustomNodeSDK

router = APIRouter(prefix="/api/developer", tags=["developer"])

_doc_generator = APIDocGenerator()
_node_sdk = CustomNodeSDK()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class NodeTemplateRequest(BaseModel):
    name: str
    category: str = "custom"
    description: str = "A custom pipeline node"


class NodeValidateRequest(BaseModel):
    code: str


class NodeRegisterRequest(BaseModel):
    name: str
    code: str
    config: dict = Field(default_factory=dict)


class NodeTestRequest(BaseModel):
    code: str
    test_input: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Documentation endpoints
# ---------------------------------------------------------------------------


@router.get("/openapi")
async def get_openapi_spec():
    """Return the full OpenAPI 3.0 spec."""
    spec = _doc_generator.generate_openapi_spec()
    return JSONResponse(content=spec)


@router.get("/postman")
async def get_postman_collection():
    """Download the Postman collection JSON."""
    collection = _doc_generator.generate_postman_collection()
    return JSONResponse(content=collection)


@router.get("/examples/{language}")
async def get_sdk_examples(language: str):
    """Return SDK usage examples for the given language (python or javascript)."""
    if language not in ("python", "javascript"):
        raise HTTPException(status_code=400, detail="Supported languages: python, javascript")
    docs = _doc_generator.generate_sdk_docs(language)
    return PlainTextResponse(content=docs)


# ---------------------------------------------------------------------------
# Custom node endpoints
# ---------------------------------------------------------------------------


@router.post("/nodes/template")
async def create_node_template(body: NodeTemplateRequest):
    """Generate a custom node template."""
    template = _node_sdk.create_node_template(body.name, body.category, body.description)
    return JSONResponse(content=template)


@router.post("/nodes/validate")
async def validate_node(body: NodeValidateRequest):
    """Validate custom node code."""
    result = _node_sdk.validate_custom_node(body.code)
    return JSONResponse(content=result)


@router.post("/nodes/register")
async def register_node(body: NodeRegisterRequest):
    """Register a custom node for the current workspace."""
    # V1: workspace_id is a placeholder
    workspace_id = "00000000-0000-0000-0000-000000000001"
    result = _node_sdk.register_custom_node(
        db=None,
        workspace_id=workspace_id,
        name=body.name,
        code=body.code,
        config=body.config,
    )
    status = 201 if result.get("registered") else 400
    return JSONResponse(content=result, status_code=status)


@router.get("/nodes")
async def list_nodes():
    """List all custom nodes for the current workspace."""
    workspace_id = "00000000-0000-0000-0000-000000000001"
    nodes = _node_sdk.list_custom_nodes(db=None, workspace_id=workspace_id)
    return JSONResponse(content={"nodes": nodes, "total": len(nodes)})


@router.post("/nodes/test")
async def test_node(body: NodeTestRequest):
    """Test a custom node with sample input."""
    result = _node_sdk.test_custom_node(body.code, body.test_input)
    status = 200 if result.get("error") is None else 422
    return JSONResponse(content=result, status_code=status)


# ---------------------------------------------------------------------------
# gRPC proto download
# ---------------------------------------------------------------------------


@router.get("/grpc/proto")
async def get_grpc_proto():
    """Download the gRPC proto definition file."""
    if not PROTO_PATH.exists():
        raise HTTPException(status_code=404, detail="Proto file not found")
    content = PROTO_PATH.read_text(encoding="utf-8")
    return PlainTextResponse(content=content, media_type="text/plain")
