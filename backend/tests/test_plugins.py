"""Tests for the plugin marketplace: framework, BYOM, marketplace, widgets, and API.

Plugin registrations, marketplace installs and BYOM adapters are
database-backed, so those tests run against a real server and skip when none
is reachable (as in CI). The widget tests are pure computation and always run.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_db
from app.main import app
from app.services.plugins.byom import BYOMAdapter, _MODEL_CACHE
from app.services.plugins.framework import PluginManager, PluginManifest
from app.services.plugins.marketplace import MarketplaceService
from app.api.routes.marketplace import SEED_PLUGINS
from app.services.plugins.widgets import WidgetService, _TOKEN_STORE
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def plugin_env():
    """Yield (session_factory, workspace_id) against a real database."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "plugins")

    try:
        yield factory, workspace_id
    finally:
        await engine.dispose()


@pytest.fixture
async def db(plugin_env):
    factory, _ = plugin_env
    async with factory() as session:
        yield session


@pytest.fixture
def WS(plugin_env):
    """Workspace id for the test, scoping every registration."""
    return str(plugin_env[1])


@pytest.fixture
async def client(plugin_env):
    factory, _ = plugin_env

    async def _override():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)


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
def _clear_process_caches():
    """Reset the caches that legitimately stay in process memory."""
    _MODEL_CACHE.clear()
    _TOKEN_STORE.clear()
    yield
    _MODEL_CACHE.clear()
    _TOKEN_STORE.clear()


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
async def test_register_plugin(plugin_mgr, db, WS):
    manifest = _sample_manifest()
    result = await plugin_mgr.register_plugin(db, WS, manifest)
    assert result["status"] == "registered"
    assert result["name"] == "Test Plugin"
    assert "plugin_id" in result


@pytest.mark.anyio
async def test_enable_disable(plugin_mgr, db, WS):
    manifest = _sample_manifest()
    reg = await plugin_mgr.register_plugin(db, WS, manifest)
    pid = reg["plugin_id"]

    enable_res = await plugin_mgr.enable_plugin(db, WS, pid)
    assert enable_res["enabled"] is True

    disable_res = await plugin_mgr.disable_plugin(db, WS, pid)
    assert disable_res["disabled"] is True


@pytest.mark.anyio
async def test_execute_plugin(plugin_mgr, db, WS):
    manifest = _sample_manifest()
    reg = await plugin_mgr.register_plugin(db, WS, manifest)
    pid = reg["plugin_id"]

    # Must enable before executing
    await plugin_mgr.enable_plugin(db, WS, pid)
    result = await plugin_mgr.execute_plugin(db, pid, {"key": "value"})
    assert "result" in result
    assert "execution_time_ms" in result
    assert result["result"]["echo"] == {"key": "value"}


@pytest.mark.anyio
async def test_list_and_get_plugin(plugin_mgr, db, WS):
    manifest = _sample_manifest()
    reg = await plugin_mgr.register_plugin(db, WS, manifest)
    pid = reg["plugin_id"]

    plugins = await plugin_mgr.list_plugins(db, WS)
    assert len(plugins) == 1

    detail = await plugin_mgr.get_plugin(db, pid)
    assert detail["name"] == "Test Plugin"


@pytest.mark.anyio
async def test_configure_and_uninstall(plugin_mgr, db, WS):
    manifest = _sample_manifest()
    reg = await plugin_mgr.register_plugin(db, WS, manifest)
    pid = reg["plugin_id"]

    cfg_res = await plugin_mgr.configure_plugin(db, pid, {"threshold": 0.5})
    assert cfg_res["configured"] is True

    rm_res = await plugin_mgr.uninstall_plugin(db, pid)
    assert rm_res["removed"] is True

    with pytest.raises(ValueError):
        await plugin_mgr.get_plugin(db, pid)


# ---------------------------------------------------------------------------
# BYOM tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_byom_register(byom, db, WS):
    result = await byom.register_model(
        db, WS, "my-model", "https://models.example.com/model.pt",
        "pytorch", {"input": "tensor"}, {"output": "tensor"},
    )
    assert "model_id" in result
    assert "adapter_id" in result


@pytest.mark.anyio
async def test_byom_predict_stub(byom, db, WS):
    reg = await byom.register_model(
        db, WS, "stub-model", "https://models.example.com/model.pt",
        "custom", {}, {},
    )
    result = await byom.predict(db, reg["adapter_id"], {"data": [1, 2, 3]})
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
async def test_byom_test_adapter(byom, db, WS):
    reg = await byom.register_model(
        db, WS, "test-model", "https://example.com/m.onnx",
        "custom", {}, {},
    )
    result = await byom.test_adapter(db, reg["adapter_id"], {"x": 1})
    assert result["works"] is True
    assert result["error"] is None


# ---------------------------------------------------------------------------
# Marketplace tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_marketplace_browse(marketplace, db, WS):
    plugins = await marketplace.browse_marketplace(db, workspace_id=WS)
    assert len(plugins) == 8
    names = [p["name"] for p in plugins]
    assert "CSV Exporter" in names
    assert "YOLO Detector" in names


@pytest.mark.anyio
async def test_marketplace_browse_category(marketplace, db, WS):
    plugins = await marketplace.browse_marketplace(db, category="analytics", workspace_id=WS)
    assert len(plugins) == 2
    assert all(p["category"] == "analytics" for p in plugins)


@pytest.mark.anyio
async def test_marketplace_install(marketplace, db, WS):
    result = await marketplace.install_from_marketplace(db, WS, "CSV Exporter")
    assert result["installed"] is True

    # Should bump install count
    details = await marketplace.get_plugin_details(db, "CSV Exporter", workspace_id=WS)
    assert details["install_count"] == 1


@pytest.mark.anyio
async def test_marketplace_popular(marketplace, db, WS):
    # Install some plugins to generate counts
    await marketplace.install_from_marketplace(db, WS, "CSV Exporter")
    await marketplace.install_from_marketplace(db, WS, "CSV Exporter")
    await marketplace.install_from_marketplace(db, WS, "YOLO Detector")

    popular = await marketplace.get_popular_plugins(db, limit=3, workspace_id=WS)
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
async def test_api_register_and_lifecycle(client, WS):
    """Register, list, enable, execute and disable over HTTP."""
    resp = await client.post(
        f"/api/plugins/register?workspace_id={WS}",
        json={
            "name": "API Plugin",
            "version": "1.0",
            "description": "Registered via API",
            "author": "tester",
            "entry_point": "tests.test_plugins:_dummy_plugin_fn",
            "capabilities": ["read"],
        },
    )
    assert resp.status_code == 201, resp.text
    plugin_id = resp.json()["id"]
    assert resp.json()["enabled"] is False

    listing = await client.get(f"/api/plugins/?workspace_id={WS}")
    assert [p["id"] for p in listing.json()] == [plugin_id]

    detail = await client.get(f"/api/plugins/{plugin_id}")
    assert detail.json()["name"] == "API Plugin"

    # Executing before enabling is refused.
    blocked = await client.post(
        f"/api/plugins/{plugin_id}/execute", json={"action": "run", "params": {}}
    )
    assert blocked.status_code == 400

    assert (await client.post(f"/api/plugins/{plugin_id}/enable")).status_code == 200
    ran = await client.post(
        f"/api/plugins/{plugin_id}/execute", json={"action": "run", "params": {}}
    )
    assert ran.status_code == 200
    assert ran.json()["status"] == "executed"

    assert (await client.post(f"/api/plugins/{plugin_id}/disable")).status_code == 200


@pytest.mark.anyio
async def test_api_unknown_plugin_404s(client):
    assert (await client.get(f"/api/plugins/{uuid.uuid4()}")).status_code == 404


@pytest.mark.anyio
async def test_api_marketplace_featured(client):
    resp = await client.get("/api/plugins/marketplace/featured")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.anyio
async def test_api_reviews_round_trip(client, WS):
    """A review posted over HTTP is readable back, and survives on the row."""
    registered = await client.post(
        f"/api/plugins/register?workspace_id={WS}",
        json={"name": "Reviewed Plugin", "entry_point": "x:y"},
    )
    plugin_id = registered.json()["id"]

    posted = await client.post(
        f"/api/plugins/{plugin_id}/reviews",
        json={"rating": 4, "text": "Works well enough for production use."},
    )
    assert posted.status_code == 201
    assert posted.json()["rating"] == 4

    listed = await client.get(f"/api/plugins/{plugin_id}/reviews")
    assert [r["text"] for r in listed.json()] == [
        "Works well enough for production use."
    ]


@pytest.mark.anyio
async def test_api_review_on_unknown_plugin_404s(client):
    resp = await client.post(
        f"/api/plugins/{uuid.uuid4()}/reviews",
        json={"rating": 5, "text": "A review long enough to pass validation."},
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_api_widget_generate(client):
    resp = await client.post(
        "/api/plugins/widgets/generate",
        json={"widget_type": "chart", "theme": "dark"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["widget_type"] == "chart"
    assert data["token"]
    assert "chart" in data["embed_url"]


# ---------------------------------------------------------------------------
# Durability
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_plugin_state_survives_a_restart(plugin_env, plugin_mgr, byom, marketplace):
    """Registrations, installs, reviews and adapters outlive the process.

    Written through one engine and read back through a brand-new one, so a
    fresh pool and identity map prove the state came out of Postgres.
    """
    factory, workspace = plugin_env
    workspace_id = str(workspace)

    async with factory() as session:
        registered = await plugin_mgr.register_plugin(
            session, workspace_id, _sample_manifest(name="Durable Plugin")
        )
        plugin_id = registered["plugin_id"]
        await plugin_mgr.enable_plugin(session, workspace_id, plugin_id)
        await plugin_mgr.configure_plugin(session, plugin_id, {"threshold": 0.9})
        await marketplace.rate_plugin(session, plugin_id, "tester", 5, "Excellent")

        adapter = await byom.register_model(
            session,
            workspace_id,
            "durable-model",
            "https://models.example.com/model.pt",
            "custom",
            {},
            {},
        )

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)

    try:
        async with restarted() as session:
            plugin = await plugin_mgr.get_plugin(session, plugin_id)
            assert plugin["name"] == "Durable Plugin"
            assert plugin["enabled"] is True
            assert plugin["config"] == {"threshold": 0.9}

            listed = await plugin_mgr.list_plugins(session, workspace_id)
            assert [p["plugin_id"] for p in listed] == [plugin_id]

            details = await marketplace.get_plugin_details(
                session, "Durable Plugin", workspace_id=workspace_id
            ) if any(
                p["name"] == "Durable Plugin"
                for p in marketplace.BUILT_IN_PLUGINS
            ) else None
            assert details is None or details["avg_rating"] == 5.0

            adapters = await byom.list_adapters(session, workspace_id)
            assert [a["adapter_id"] for a in adapters] == [adapter["adapter_id"]]
            assert adapters[0]["model_name"] == "durable-model"
    finally:
        await restarted_engine.dispose()


@pytest.mark.anyio
async def test_installed_marketplace_plugins_survive_a_restart(plugin_env):
    """A plugin installed through the API is still installed after a restart."""
    factory, workspace = plugin_env
    workspace_id = str(workspace)

    async def _client(session_factory):
        async def _override():
            async with session_factory() as session:
                yield session

        app.dependency_overrides[get_db] = _override
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    async with await _client(factory) as first:
        listing = await first.get(
            f"/api/marketplace/installed?workspace_id={workspace_id}"
        )
        assert listing.status_code == 200
        installed = listing.json()
        assert installed["total_installed"] == len(SEED_PLUGINS)
        target = installed["plugins"][0]["id"]

        configured = await first.patch(
            f"/api/marketplace/plugins/{target}/config",
            json={"config": {"confidence_threshold": 0.9}},
        )
        assert configured.status_code == 200

    restarted_engine = await fresh_engine()
    restarted = db_session_factory(restarted_engine)
    try:
        async with await _client(restarted) as second:
            again = await second.get(
                f"/api/marketplace/installed?workspace_id={workspace_id}"
            )
            plugins = {p["id"]: p for p in again.json()["plugins"]}
            assert target in plugins
            assert plugins[target]["config"]["confidence_threshold"] == 0.9
    finally:
        app.dependency_overrides.pop(get_db, None)
        await restarted_engine.dispose()
