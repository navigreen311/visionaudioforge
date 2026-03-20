"""Tests for gRPC API definitions, custom node SDK, and developer tools."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.grpc.server import VAFGRPCServer, PROTO_PATH
from app.services.plugins.node_sdk import CustomNodeSDK
from app.services.plugins.api_docs import APIDocGenerator
from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def node_sdk():
    return CustomNodeSDK()


@pytest.fixture
def valid_node_code():
    return textwrap.dedent("""\
        from visionaudioforge.pipeline import BaseNode

        class MyCustomNode(BaseNode):
            name = "my_custom"
            category = "transform"
            input_schema = {"data": "any"}
            output_schema = {"result": "any"}

            async def execute(self, inputs):
                return {"result": inputs.get("data")}
    """)


@pytest.fixture
def missing_execute_code():
    return textwrap.dedent("""\
        from visionaudioforge.pipeline import BaseNode

        class BrokenNode(BaseNode):
            name = "broken"
            category = "custom"
            input_schema = {"data": "any"}
            output_schema = {"result": "any"}
    """)


@pytest.fixture
def missing_base_code():
    return textwrap.dedent("""\
        class NotANode:
            name = "not_a_node"
            async def execute(self, inputs):
                return {}
    """)


# ---------------------------------------------------------------------------
# Proto / gRPC server tests
# ---------------------------------------------------------------------------

def test_proto_file_valid_syntax():
    """Proto file exists and contains expected service definitions."""
    assert PROTO_PATH.exists(), "vaf.proto not found"
    content = PROTO_PATH.read_text(encoding="utf-8")
    assert 'syntax = "proto3"' in content
    assert "service VisionService" in content
    assert "service AudioService" in content
    assert "service InferenceService" in content
    assert "service SearchService" in content
    assert "message ImageRequest" in content
    assert "message PredictRequest" in content
    assert "message SearchQuery" in content


@pytest.mark.anyio
async def test_grpc_server_stub_init():
    """VAFGRPCServer initialises and start() returns V1 stub message."""
    server = VAFGRPCServer(port=50052)
    assert server.port == 50052
    assert server.is_running is False

    msg = await server.start()
    assert server.is_running is True
    assert "50052" in msg
    assert "grpcio" in msg

    await server.stop()
    assert server.is_running is False


# ---------------------------------------------------------------------------
# Custom Node SDK tests
# ---------------------------------------------------------------------------

def test_node_template_generation(node_sdk):
    """create_node_template returns valid template with correct class name."""
    result = node_sdk.create_node_template("image_filter", "vision", "Filters images")
    assert result["name"] == "image_filter"
    assert result["category"] == "vision"
    assert "ImageFilterNode" in result["class_name"]
    assert "class ImageFilterNode(BaseNode)" in result["code"]
    assert 'name = "image_filter"' in result["code"]


def test_node_validation_valid_code(node_sdk, valid_node_code):
    """Valid node code passes validation."""
    result = node_sdk.validate_custom_node(valid_node_code)
    assert result["valid"] is True
    assert result["errors"] == []


def test_node_validation_missing_execute(node_sdk, missing_execute_code):
    """Node code without execute method fails validation."""
    result = node_sdk.validate_custom_node(missing_execute_code)
    assert result["valid"] is False
    assert any("execute" in e for e in result["errors"])


def test_node_validation_missing_base(node_sdk, missing_base_code):
    """Code without BaseNode subclass fails validation."""
    result = node_sdk.validate_custom_node(missing_base_code)
    assert result["valid"] is False
    assert any("BaseNode" in e for e in result["errors"])


def test_custom_node_registration(node_sdk, valid_node_code):
    """register_custom_node stores the node and list_custom_nodes returns it."""
    result = node_sdk.register_custom_node(
        db=None,
        workspace_id="ws-test-001",
        name="test_node",
        code=valid_node_code,
        config={"enabled": True},
    )
    assert result["registered"] is True
    assert result["node_id"] is not None

    nodes = node_sdk.list_custom_nodes(db=None, workspace_id="ws-test-001")
    assert any(n["name"] == "test_node" for n in nodes)


# ---------------------------------------------------------------------------
# API Documentation tests
# ---------------------------------------------------------------------------

def test_openapi_spec_generation():
    """OpenAPI spec contains expected fields and security scheme."""
    gen = APIDocGenerator(app=app)
    spec = gen.generate_openapi_spec()
    assert spec["info"]["title"] == "VisionAudioForge API"
    assert "paths" in spec
    assert "components" in spec
    assert "BearerAuth" in spec["components"]["securitySchemes"]


def test_postman_collection():
    """Postman collection has correct schema and non-empty items."""
    gen = APIDocGenerator(app=app)
    collection = gen.generate_postman_collection()
    assert "info" in collection
    assert collection["info"]["name"] == "VisionAudioForge API"
    assert "item" in collection
    assert len(collection["item"]) > 0


def test_curl_examples():
    """Curl examples dict has entries for known endpoints."""
    gen = APIDocGenerator(app=app)
    examples = gen.generate_curl_examples()
    assert isinstance(examples, dict)
    assert len(examples) > 0
    # All values should be curl commands
    for key, cmd in examples.items():
        assert cmd.startswith("curl")


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_api_template(client):
    """POST /api/developer/nodes/template returns generated code."""
    resp = await client.post(
        "/api/developer/nodes/template",
        json={"name": "edge_detect", "category": "vision"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "code" in data
    assert "EdgeDetectNode" in data["code"]


@pytest.mark.anyio
async def test_api_validate(client, valid_node_code):
    """POST /api/developer/nodes/validate returns valid=True for good code."""
    resp = await client.post(
        "/api/developer/nodes/validate",
        json={"code": valid_node_code},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


@pytest.mark.anyio
async def test_api_proto(client):
    """GET /api/developer/grpc/proto returns the proto file content."""
    resp = await client.get("/api/developer/grpc/proto")
    assert resp.status_code == 200
    assert "service VisionService" in resp.text
    assert "proto3" in resp.text
