"""Tests for the Pipeline Builder feature (M16) and NL generation / templates (P2-17)."""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.services.pipeline.engine import PipelineEngine
from app.services.pipeline.nl_generator import NLPipelineGenerator
from app.services.pipeline.nodes import NODE_REGISTRY, get_node
from app.services.pipeline.templates import PIPELINE_TEMPLATES, list_templates


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

def test_node_registry_has_26_nodes():
    # 21 original + 5 new (conditional, loop, delay, log, http_request) = 26
    assert len(NODE_REGISTRY) >= 26


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


# ---------------------------------------------------------------------------
# NL Pipeline Generator tests (P2-17)
# ---------------------------------------------------------------------------

@pytest.fixture
def nl_generator():
    return NLPipelineGenerator()


@pytest.mark.asyncio
async def test_nl_generator_parses_description(nl_generator):
    """Generate a pipeline from 'detect objects in images'."""
    result = await nl_generator.generate_from_description("detect objects in images")
    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) >= 2
    node_types = [n["type"] for n in result["nodes"]]
    assert "input_image" in node_types
    assert "detect_objects" in node_types


@pytest.mark.asyncio
async def test_nl_generator_detects_keywords(nl_generator):
    """Audio-related description should produce audio pipeline nodes."""
    result = await nl_generator.generate_from_description("analyze audio for speech recognition")
    node_types = [n["type"] for n in result["nodes"]]
    assert "input_audio" in node_types
    assert "stft" in node_types or "mfcc" in node_types


@pytest.mark.asyncio
async def test_nl_generator_similar_images(nl_generator):
    """'find similar images' should produce CLIP + FAISS pipeline."""
    result = await nl_generator.generate_from_description("find similar images")
    node_types = [n["type"] for n in result["nodes"]]
    assert "embed_clip" in node_types
    assert "faiss_search" in node_types


@pytest.mark.asyncio
async def test_suggest_next_nodes(nl_generator):
    """Suggest next nodes after input_image should include vision nodes."""
    suggestions = await nl_generator.suggest_next_nodes(["input_image"])
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
    # Should suggest image processing nodes
    assert any(s in suggestions for s in ["normalize", "resize", "detect_objects", "embed_clip"])


@pytest.mark.asyncio
async def test_suggest_next_nodes_empty(nl_generator):
    """Empty pipeline should suggest input nodes."""
    suggestions = await nl_generator.suggest_next_nodes([])
    assert "input_image" in suggestions
    assert "input_audio" in suggestions


# ---------------------------------------------------------------------------
# Template tests (P2-17)
# ---------------------------------------------------------------------------

def test_templates_all_valid_pipelines(engine):
    """Every template should produce a valid pipeline definition."""
    assert len(PIPELINE_TEMPLATES) >= 10
    for key, template in PIPELINE_TEMPLATES.items():
        assert "name" in template, f"Template '{key}' missing name"
        assert "description" in template, f"Template '{key}' missing description"
        assert "category" in template, f"Template '{key}' missing category"
        assert "definition" in template, f"Template '{key}' missing definition"
        defn = template["definition"]
        assert "nodes" in defn, f"Template '{key}' definition missing nodes"
        assert "edges" in defn, f"Template '{key}' definition missing edges"
        # Validate with the engine (nodes must be valid types, no cycles)
        result = engine.validate_pipeline(defn)
        assert result["valid"] is True, f"Template '{key}' invalid: {result['errors']}"


def test_list_templates_returns_all():
    """list_templates() should return all 10 templates."""
    result = list_templates()
    assert len(result) >= 10
    keys = {t["key"] for t in result}
    assert "image-preprocessing" in keys
    assert "object-detection" in keys
    assert "audio-analysis" in keys


# ---------------------------------------------------------------------------
# Conditional node test (P2-17)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_conditional_node():
    """ConditionalNode should route based on condition key."""
    node = get_node("conditional")
    # True branch
    result = await node.execute({"data": {"active": True}, "condition": "active"})
    assert result["branch"] == "true"
    assert result["output_true"] is not None
    assert result["output_false"] is None

    # False branch
    result = await node.execute({"data": {"active": False}, "condition": "active"})
    assert result["branch"] == "false"
    assert result["output_true"] is None
    assert result["output_false"] is not None


@pytest.mark.asyncio
async def test_loop_node():
    """LoopNode should iterate the specified number of times."""
    node = get_node("loop")
    result = await node.execute({"data": {"value": 42}, "iterations": 5})
    assert result["iteration_count"] == 5
    assert result["output"]["value"] == 42


@pytest.mark.asyncio
async def test_log_node():
    """LogNode should pass data through unchanged."""
    node = get_node("log")
    result = await node.execute({"data": {"key": "value"}, "label": "test"})
    assert result["data"] == {"key": "value"}


# ---------------------------------------------------------------------------
# API tests for new endpoints (P2-17)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_generate(client):
    """POST /api/pipeline/generate should return a pipeline definition."""
    resp = await client.post(
        "/api/pipeline/generate",
        json={"description": "detect objects in images"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "definition" in data
    assert "nodes" in data["definition"]
    assert "edges" in data["definition"]


@pytest.mark.asyncio
async def test_api_templates_list(client):
    """GET /api/pipeline/templates should return the template catalog."""
    resp = await client.get("/api/pipeline/templates")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 10
    # Each template should have name, description, category, definition
    for t in data:
        assert "name" in t
        assert "definition" in t


@pytest.mark.asyncio
async def test_api_template_by_name(client):
    """GET /api/pipeline/templates/{name} should return a specific template."""
    resp = await client.get("/api/pipeline/templates/image-preprocessing")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Image Preprocessing"
    assert "definition" in data


@pytest.mark.asyncio
async def test_api_suggest_next(client):
    """POST /api/pipeline/suggest-next should return suggestions."""
    resp = await client.post(
        "/api/pipeline/suggest-next",
        json={"current_nodes": ["input_image", "normalize"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "suggestions" in data
    assert isinstance(data["suggestions"], list)
