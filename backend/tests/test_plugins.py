"""Tests for the plugin marketplace: framework, BYOM, marketplace, widgets, and API."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.main import app
from app.services.plugins.framework import PluginManager, PluginManifest, _PLUGIN_STORE
from app.services.plugins.byom import BYOMAdapter, _ADAPTER_STORE, _MODEL_CACHE
from app.services.plugins.marketplace import MarketplaceService
from app.services.plugins.widgets import WidgetService, _TOKEN_STORE


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
def plugin_mgr():
    return PluginManager()


@pytest.fixture
def byom():
    return BYOMAdapter()


@pytest.fixture
def marketplace():
    return MarketplaceService()


@pytest.fixture
def widget_svc():
    return WidgetService()


@pytest.fixture(autouse=True)
def _clear_stores():
    """Clear in-memory stores before each test."""
    _PLUGIN_STORE.clear()
    _ADAPTER_STORE.clear()
    _MODEL_CACHE.clear()
    _TOKEN_STORE.clear()
    yield
    _PLUGIN_STORE.clear()
    _ADAPTER_STORE.clear()
    _MODEL_CACHE.clear()
    _TOKEN_STORE.clear()


WS = "ws-test-001"
DB = None  # Stub — services accept but don't use DB in V1


def _sample_manifest(**overrides) -> PluginManifest:
    defaults = {
        "name": "Test Plugin",
        "version": "1.0",
        "author": "tester",
        "description": "A test plugin",
        "category": "transform",
        "entry_point": "tests.test_plugins:_dummy_plugin_fn",
        "permissions": ["read"],
        "config_schema": {},
        "icon_url": None,
    }
    defaults.update(overrides)
    return PluginManifest(**defaults)


def _dummy_plugin_fn(input_data: dict, config: dict | None = None) -> dict:
    """Trivial plugin function used for execution tests."""
    return {"echo": input_data}


# ---------------------------------------------------------------------------
# PluginManager tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_register_plugin(plugin_mgr):
    manifest = _sample_manifest()
    result = await plugin_mgr.register_plugin(DB, WS, manifest)
    assert result["status"] == "registered"
    assert result["name"] == "Test Plugin"
    assert "plugin_id" in result


@pytest.mark.anyio
async def test_enable_disable(plugin_mgr):
    manifest = _sample_manifest()
    reg = await plugin_mgr.register_plugin(DB, WS, manifest)
    pid = reg["plugin_id"]

    enable_res = await plugin_mgr.enable_plugin(DB, WS, pid)
    assert enable_res["enabled"] is True

    disable_res = await plugin_mgr.disable_plugin(DB, WS, pid)
    assert disable_res["disabled"] is True


@pytest.mark.anyio
async def test_execute_plugin(plugin_mgr):
    manifest = _sample_manifest()
    reg = await plugin_mgr.register_plugin(DB, WS, manifest)
    pid = reg["plugin_id"]

    # Must enable before executing
    await plugin_mgr.enable_plugin(DB, WS, pid)
    result = await plugin_mgr.execute_plugin(pid, {"key": "value"})
    assert "result" in result
    assert "execution_time_ms" in result
    assert result["result"]["echo"] == {"key": "value"}


@pytest.mark.anyio
async def test_list_and_get_plugin(plugin_mgr):
    manifest = _sample_manifest()
    reg = await plugin_mgr.register_plugin(DB, WS, manifest)
    pid = reg["plugin_id"]

    plugins = await plugin_mgr.list_plugins(DB, WS)
    assert len(plugins) == 1

    detail = await plugin_mgr.get_plugin(DB, pid)
    assert detail["name"] == "Test Plugin"


@pytest.mark.anyio
async def test_configure_and_uninstall(plugin_mgr):
    manifest = _sample_manifest()
    reg = await plugin_mgr.register_plugin(DB, WS, manifest)
    pid = reg["plugin_id"]

    cfg_res = await plugin_mgr.configure_plugin(DB, pid, {"threshold": 0.5})
    assert cfg_res["configured"] is True

    rm_res = await plugin_mgr.uninstall_plugin(DB, pid)
    assert rm_res["removed"] is True

    with pytest.raises(ValueError):
        await plugin_mgr.get_plugin(DB, pid)


# ---------------------------------------------------------------------------
# BYOM tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_byom_register(byom):
    result = await byom.register_model(
        DB, WS, "my-model", "https://models.example.com/model.pt",
        "pytorch", {"input": "tensor"}, {"output": "tensor"},
    )
    assert "model_id" in result
    assert "adapter_id" in result


@pytest.mark.anyio
async def test_byom_predict_stub(byom):
    reg = await byom.register_model(
        DB, WS, "stub-model", "https://models.example.com/model.pt",
        "custom", {}, {},
    )
    result = await byom.predict(reg["adapter_id"], {"data": [1, 2, 3]})
    assert "prediction" in result
    assert "latency_ms" in result
    assert result["prediction"]["framework"] == "custom"


@pytest.mark.anyio
async def test_supported_frameworks(byom):
    frameworks = byom.get_supported_frameworks()
    names = [f["framework"] for f in frameworks]
    assert "pytorch" in names
    assert "tensorflow" in names
    assert "onnx" in names
    assert "sklearn" in names
    assert "custom" in names


@pytest.mark.anyio
async def test_byom_test_adapter(byom):
    reg = await byom.register_model(
        DB, WS, "test-model", "https://example.com/m.onnx",
        "custom", {}, {},
    )
    result = await byom.test_adapter(reg["adapter_id"], {"x": 1})
    assert result["works"] is True
    assert result["error"] is None


# ---------------------------------------------------------------------------
# Marketplace tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_marketplace_browse(marketplace):
    plugins = await marketplace.browse_marketplace()
    assert len(plugins) == 8
    names = [p["name"] for p in plugins]
    assert "CSV Exporter" in names
    assert "YOLO Detector" in names


@pytest.mark.anyio
async def test_marketplace_browse_category(marketplace):
    plugins = await marketplace.browse_marketplace(category="analytics")
    assert len(plugins) == 2
    assert all(p["category"] == "analytics" for p in plugins)


@pytest.mark.anyio
async def test_marketplace_install(marketplace):
    result = await marketplace.install_from_marketplace(DB, WS, "CSV Exporter")
    assert result["installed"] is True

    # Should bump install count
    details = await marketplace.get_plugin_details("CSV Exporter")
    assert details["install_count"] == 1


@pytest.mark.anyio
async def test_marketplace_popular(marketplace):
    # Install some plugins to generate counts
    await marketplace.install_from_marketplace(DB, WS, "CSV Exporter")
    await marketplace.install_from_marketplace(DB, WS, "CSV Exporter")
    await marketplace.install_from_marketplace(DB, WS, "YOLO Detector")

    popular = await marketplace.get_popular_plugins(limit=3)
    assert len(popular) <= 3
    assert popular[0]["name"] == "CSV Exporter"


# ---------------------------------------------------------------------------
# Widget tests
# ---------------------------------------------------------------------------


def test_widget_types(widget_svc):
    types = widget_svc.get_widget_types()
    assert "live_feed" in types
    assert "copilot_mini" in types
    assert len(types) == 6


def test_embed_code_generation(widget_svc):
    result = widget_svc.generate_embed_code("chart", {"workspace_id": "ws-1"})
    assert "html" in result
    assert "script_url" in result
    assert "iframe_url" in result
    assert "chart" in result["iframe_url"]
    assert "<iframe" in result["html"]


@pytest.mark.anyio
async def test_embed_token_validation(widget_svc):
    result = widget_svc.generate_embed_code("metric_card", {"workspace_id": "ws-1"})
    # Extract token from iframe_url
    token = result["iframe_url"].split("token=")[1]
    validation = await widget_svc.validate_embed_token(token)
    assert validation["valid"] is True
    assert validation["widget_type"] == "metric_card"

    # Invalid token
    bad = await widget_svc.validate_embed_token("nope")
    assert bad["valid"] is False


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_register(client):
    resp = await client.post("/api/plugins/register", json={
        "workspace_id": WS,
        "manifest": {
            "name": "API Plugin",
            "version": "1.0",
            "author": "tester",
            "description": "Registered via API",
            "category": "analytics",
            "entry_point": "tests.test_plugins:_dummy_plugin_fn",
            "permissions": [],
            "config_schema": {},
            "icon_url": None,
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "registered"


@pytest.mark.anyio
async def test_api_marketplace(client):
    resp = await client.get("/api/plugins/marketplace")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8


@pytest.mark.anyio
async def test_api_marketplace_install(client):
    resp = await client.post("/api/plugins/marketplace/install", json={
        "workspace_id": WS,
        "plugin_name": "Slack Notifier",
    })
    assert resp.status_code == 200
    assert resp.json()["installed"] is True


@pytest.mark.anyio
async def test_api_byom(client):
    resp = await client.post("/api/plugins/byom", json={
        "workspace_id": WS,
        "model_name": "api-model",
        "model_path_or_url": "https://example.com/model.onnx",
        "framework": "onnx",
        "input_schema": {},
        "output_schema": {},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "adapter_id" in data

    # Predict
    aid = data["adapter_id"]
    pred = await client.post(f"/api/plugins/byom/{aid}/predict", json={
        "input_data": {"x": 42},
    })
    assert pred.status_code == 200
    assert "prediction" in pred.json()


@pytest.mark.anyio
async def test_api_widgets(client):
    resp = await client.get("/api/plugins/widgets")
    assert resp.status_code == 200
    assert "live_feed" in resp.json()


@pytest.mark.anyio
async def test_api_embed(client):
    resp = await client.post("/api/plugins/widgets/embed", json={
        "widget_type": "chart",
        "config": {"workspace_id": "ws-1"},
    })
    assert resp.status_code == 200
    assert "<iframe" in resp.json()["html"]
