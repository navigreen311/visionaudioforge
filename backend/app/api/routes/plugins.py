"""Plugin marketplace API routes — plugins, BYOM, marketplace, widgets."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any

from app.core.deps import get_db
from app.services.plugins.framework import PluginManager, PluginManifest
from app.services.plugins.byom import BYOMAdapter
from app.services.plugins.marketplace import MarketplaceService
from app.services.plugins.widgets import WidgetService

router = APIRouter(prefix="/api/plugins", tags=["plugins"])

plugin_mgr = PluginManager()
byom_adapter = BYOMAdapter()
marketplace_svc = MarketplaceService()
widget_svc = WidgetService()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class RegisterPluginRequest(BaseModel):
    workspace_id: str
    manifest: PluginManifest


class ConfigurePluginRequest(BaseModel):
    config: dict


class ExecutePluginRequest(BaseModel):
    input_data: dict


class BYOMRegisterRequest(BaseModel):
    workspace_id: str
    model_name: str
    model_path_or_url: str
    framework: str
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)


class BYOMPredictRequest(BaseModel):
    input_data: dict


class MarketplaceInstallRequest(BaseModel):
    workspace_id: str
    plugin_name: str


class RatePluginRequest(BaseModel):
    user_id: str
    rating: int
    review: str


class EmbedRequest(BaseModel):
    widget_type: str
    config: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Plugin CRUD routes
# ---------------------------------------------------------------------------


@router.post("/register")
async def register_plugin(body: RegisterPluginRequest, db=Depends(get_db)):
    try:
        result = await plugin_mgr.register_plugin(db, body.workspace_id, body.manifest)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("")
async def list_plugins(
    workspace_id: str = Query(...),
    category: str | None = Query(None),
    enabled: bool | None = Query(None),
    db=Depends(get_db),
):
    return await plugin_mgr.list_plugins(db, workspace_id, category, enabled)


@router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    workspace_id: str = Query(...),
    db=Depends(get_db),
):
    try:
        return await plugin_mgr.enable_plugin(db, workspace_id, plugin_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    workspace_id: str = Query(...),
    db=Depends(get_db),
):
    try:
        return await plugin_mgr.disable_plugin(db, workspace_id, plugin_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, body: ExecutePluginRequest):
    try:
        return await plugin_mgr.execute_plugin(plugin_id, body.input_data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{plugin_id}/configure")
async def configure_plugin(
    plugin_id: str, body: ConfigurePluginRequest, db=Depends(get_db)
):
    try:
        return await plugin_mgr.configure_plugin(db, plugin_id, body.config)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{plugin_id}")
async def uninstall_plugin(plugin_id: str, db=Depends(get_db)):
    try:
        return await plugin_mgr.uninstall_plugin(db, plugin_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{plugin_id}/rate")
async def rate_plugin(plugin_id: str, body: RatePluginRequest, db=Depends(get_db)):
    try:
        return await marketplace_svc.rate_plugin(
            db, plugin_id, body.user_id, body.rating, body.review
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# BYOM routes
# ---------------------------------------------------------------------------


@router.post("/byom")
async def register_byom(body: BYOMRegisterRequest, db=Depends(get_db)):
    try:
        return await byom_adapter.register_model(
            db,
            body.workspace_id,
            body.model_name,
            body.model_path_or_url,
            body.framework,
            body.input_schema,
            body.output_schema,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/byom/{adapter_id}/predict")
async def byom_predict(adapter_id: str, body: BYOMPredictRequest):
    try:
        return await byom_adapter.predict(adapter_id, body.input_data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/byom")
async def list_byom_adapters(
    workspace_id: str = Query(...), db=Depends(get_db)
):
    return await byom_adapter.list_adapters(db, workspace_id)


# ---------------------------------------------------------------------------
# Marketplace routes (mounted under /api/plugins but aliased below)
# ---------------------------------------------------------------------------


@router.get("/marketplace")
async def browse_marketplace(
    category: str | None = Query(None),
    search: str | None = Query(None),
):
    return await marketplace_svc.browse_marketplace(category, search)


@router.post("/marketplace/install")
async def install_from_marketplace(
    body: MarketplaceInstallRequest, db=Depends(get_db)
):
    try:
        return await marketplace_svc.install_from_marketplace(
            db, body.workspace_id, body.plugin_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Widget routes
# ---------------------------------------------------------------------------


@router.get("/widgets")
async def get_widget_types():
    return widget_svc.get_widget_types()


@router.post("/widgets/embed")
async def generate_embed_code(body: EmbedRequest):
    try:
        return widget_svc.generate_embed_code(body.widget_type, body.config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
