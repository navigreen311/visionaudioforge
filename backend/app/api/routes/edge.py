"""Edge deployment API routes — export, convert, package, and benchmark models
for edge inference."""

from __future__ import annotations

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.edge.onnx_export import ONNXExporter
from app.services.edge.converters import ModelConverter
from app.services.edge.export_pipeline import ExportPipeline

router = APIRouter(prefix="/api/edge", tags=["edge"])

_pipeline = ExportPipeline()
_exporter = ONNXExporter()
_converter = ModelConverter()


# ------------------------------------------------------------------
# Request / response schemas
# ------------------------------------------------------------------

class ExportRequest(BaseModel):
    model_id: str
    formats: list[str] = Field(default=["onnx"])
    optimization_level: str = Field(default="basic")


class PackageRequest(BaseModel):
    model_id: str
    format: str = Field(default="onnx")


class BenchmarkRequest(BaseModel):
    export_id: str
    iterations: int = Field(default=100, ge=1, le=10000)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/export")
async def export_model(body: ExportRequest):
    """Export a model to one or more edge formats."""
    try:
        result = await _pipeline.export_model(
            db=None,
            model_id=body.model_id,
            formats=body.formats,
            optimization_level=body.optimization_level,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/exports")
async def list_exports(workspace_id: str = "default"):
    """List all exports for a workspace."""
    return await _pipeline.list_exports(db=None, workspace_id=workspace_id)


@router.get("/exports/{export_id}")
async def get_export(export_id: str):
    """Get details of a specific export."""
    result = await _pipeline.get_export_status(export_id)
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Export not found")
    return result


@router.get("/exports/{export_id}/download")
async def download_export(export_id: str, format: str = "onnx"):
    """Download an exported model file."""
    try:
        path = await _pipeline.download_export(export_id, format)
        return FileResponse(path, filename=f"model.{format}")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/package")
async def create_package(body: PackageRequest):
    """Create an edge deployment package with model, config, and sample code."""
    result = await _pipeline.create_edge_package(
        db=None,
        model_id=body.model_id,
        fmt=body.format,
    )
    return result


@router.get("/formats")
async def list_formats():
    """List supported export formats with availability status."""
    return _converter.get_supported_formats()


@router.post("/benchmark")
async def benchmark_model(body: BenchmarkRequest):
    """Run inference benchmark on an exported model."""
    status = await _pipeline.get_export_status(body.export_id)
    if status.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Export not found")

    onnx_export = status.get("exports", {}).get("onnx", {})
    onnx_path = onnx_export.get("path")
    if not onnx_path:
        raise HTTPException(
            status_code=422,
            detail="No ONNX model found in this export. Benchmark requires ONNX format.",
        )

    result = _exporter.benchmark_onnx(onnx_path, iterations=body.iterations)
    result["export_id"] = body.export_id
    return result
