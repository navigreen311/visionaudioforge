"""Tests for the Pipeline Builder feature (M16)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.services.pipeline.engine import PipelineEngine
from app.services.pipeline.nodes import NODE_REGISTRY, get_node


# ---------------------------------------------------------------------------
# Engine / validation tests
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    return PipelineEngine()


def _simple_pipeline(params: dict | None = None) -> dict:
    """Two-node pipeline: input_image → normalize."""
    return {
        "nodes": [
            {"id": "n1", "type": "input_image", "params": params or {"path": "/tmp/test.png"}},
            {"id": "n2", "type": "normalize", "params": {}},
        ],
        "edges": [
            {"from": "n1", "to": "n2", "from_port": "image", "to_port": "image"},
        ],
    }


def test_validate_valid_pipeline(engine):
    result = engine.validate_pipeline(_simple_pipeline())
    assert result["valid"] is True
    assert result["errors"] == []


def test_validate_detects_cycle(engine):
    definition = {
        "nodes": [
            {"id": "a", "type": "normalize", "params": {}},
            {"id": "b", "type": "normalize", "params": {}},
        ],
        "edges": [
            {"from": "a", "to": "b", "from_port": "image", "to_port": "image"},
            {"from": "b", "to": "a", "from_port": "image", "to_port": "image"},
        ],
    }
    result = engine.validate_pipeline(definition)
    assert result["valid"] is False
    assert any("cycle" in e.lower() for e in result["errors"])


def test_validate_missing_node_type(engine):
    definition = {
        "nodes": [{"id": "n1", "type": "does_not_exist", "params": {}}],
        "edges": [],
    }
    result = engine.validate_pipeline(definition)
    assert result["valid"] is False
    assert any("Unknown node type" in e for e in result["errors"])


def test_topological_sort_correct_order(engine):
    nodes = [
        {"id": "a", "type": "input_image", "params": {}},
        {"id": "b", "type": "normalize", "params": {}},
        {"id": "c", "type": "resize", "params": {}},
    ]
    edges = [
        {"from": "a", "to": "b"},
        {"from": "b", "to": "c"},
    ]
    order = engine._topological_sort(nodes, edges)
    assert order == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# Execution test (mock image via numpy)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_simple_pipeline(engine, tmp_path):
    """InputImage → Normalize with a real tiny image file."""
    import numpy as np
    from PIL import Image

    # Create a small test image
    img_path = tmp_path / "test.png"
    img = Image.fromarray(np.random.randint(0, 255, (4, 4, 3), dtype=np.uint8))
    img.save(str(img_path))

    definition = _simple_pipeline(params={"path": str(img_path)})
    result = await engine.execute_pipeline(definition)

    assert result["status"] == "completed"
    assert "n1" in result["node_results"]
    assert "n2" in result["node_results"]
    assert result["duration_ms"] >= 0
    assert result["errors"] == []
    # Normalized image should be a float array
    norm_img = result["node_results"]["n2"]["image"]
    assert norm_img is not None


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

def test_node_registry_has_20_nodes():
    # We defined 21 nodes (extra merge), but spec says 20 minimum
    assert len(NODE_REGISTRY) >= 20


def test_get_node_returns_instance():
    node = get_node("normalize")
    assert node.name == "Normalize"
    assert node.category == "Vision"


def test_get_node_unknown_raises():
    with pytest.raises(KeyError):
        get_node("nonexistent_node")


# ---------------------------------------------------------------------------
# API tests (using httpx + ASGI transport)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_get_nodes_list(client):
    resp = await client.get("/api/pipeline/nodes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 20
    # Each entry has required fields
    entry = data[0]
    assert "type" in entry
    assert "category" in entry
    assert "inputs" in entry
    assert "outputs" in entry


@pytest.mark.asyncio
async def test_api_validate_pipeline(client):
    resp = await client.post(
        "/api/pipeline/validate",
        json={"definition": _simple_pipeline()},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_api_validate_detects_bad_pipeline(client):
    resp = await client.post(
        "/api/pipeline/validate",
        json={"definition": {"nodes": [{"id": "x", "type": "fake", "params": {}}], "edges": []}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
