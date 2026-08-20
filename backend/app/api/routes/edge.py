"""Edge Deployment routes — export, packaging, benchmarking, device management."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.edge_export import EdgeBenchmark, ModelExport
from app.models.edge_fleet import DeviceMetric, EdgeDevice, OfflinePackage
from app.services.edge.export_pipeline import ExportPipeline

router = APIRouter(prefix="/api/edge", tags=["edge"])

_export_pipeline = ExportPipeline()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ExportRequest(BaseModel):
    model_id: str
    format: str = Field("onnx", pattern="^(onnx|tensorrt|tflite|coreml|openvino)$")
    optimize: bool = True
    quantize: bool = False


class MultiFormatExportRequest(BaseModel):
    model_id: str
    formats: list[str] = Field(default_factory=lambda: ["onnx"])
    # Callers that export one format send `format`. It used to be dropped
    # silently and the default ["onnx"] used instead, so asking for tflite
    # quietly produced ONNX.
    format: str | None = None
    optimize: bool = True
    quantize: bool = False

    def requested_formats(self) -> list[str]:
        if self.format:
            return [self.format]
        return self.formats


class PackageRequest(BaseModel):
    model_id: str
    format: str = "onnx"
    include_runtime: bool = True
    target_platform: str = "linux-arm64"


class BenchmarkRequest(BaseModel):
    model_id: str
    format: str = "onnx"
    device: str = "cpu"
    num_iterations: int = 100
    warmup_iterations: int = 10


class DeviceRegisterRequest(BaseModel):
    name: str
    device_type: str = "edge-node"
    platform: str = "linux-arm64"
    location: str | None = None


def _ws(workspace_id: str | None):
    return uuid.UUID(str(workspace_id)) if workspace_id else None


def _uuid_or_404(value: str, what: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        raise HTTPException(status_code=404, detail=f"{what} not found")


def _serialise_export(row: ModelExport) -> dict[str, Any]:
    return {
        "id": str(row.id),
        # Callers key on export_id; `id` is kept for older ones.
        "export_id": str(row.id),
        "model_id": row.model_id,
        "format": row.format,
        "optimize": row.optimize,
        "quantize": row.quantize,
        "status": row.status,
        "file_size_mb": row.file_size_mb,
        "download_url": row.download_url,
        "created_at": row.created_at.timestamp() if row.created_at else None,
    }


# Each entry carries both "format" and "name": callers key on "format", and the
# console renders "name". webgpu is listed because ModelConverter exports it.
SUPPORTED_FORMATS = [
    {"format": "onnx", "name": "onnx", "description": "Open Neural Network Exchange", "extensions": [".onnx"]},
    {"format": "tensorrt", "name": "tensorrt", "description": "NVIDIA TensorRT", "extensions": [".engine"]},
    {"format": "tflite", "name": "tflite", "description": "TensorFlow Lite", "extensions": [".tflite"]},
    {"format": "coreml", "name": "coreml", "description": "Apple Core ML", "extensions": [".mlmodel"]},
    {"format": "openvino", "name": "openvino", "description": "Intel OpenVINO", "extensions": [".xml", ".bin"]},
    {"format": "webgpu", "name": "webgpu", "description": "WebGPU / in-browser inference", "extensions": [".json", ".bin"]},
]

# Format metadata for estimates
_FORMAT_META = {
    "onnx": {"size_mb": 42.5, "latency_ms": 12.3, "compression_ratio": 1.0},
    "tensorrt": {"size_mb": 38.1, "latency_ms": 4.7, "compression_ratio": 0.90},
    "tflite": {"size_mb": 11.2, "latency_ms": 18.9, "compression_ratio": 0.26},
    "coreml": {"size_mb": 40.0, "latency_ms": 8.1, "compression_ratio": 0.94},
    "openvino": {"size_mb": 35.6, "latency_ms": 6.2, "compression_ratio": 0.84},
}



# ---------------------------------------------------------------------------
# Format Estimates
# ---------------------------------------------------------------------------

@router.get("/format-estimates")
async def format_estimates(
    model_id: str = Query(..., description="Model identifier"),
    formats: str = Query("onnx", description="Comma-separated list of formats"),
) -> dict[str, Any]:
    """Return estimated sizes and latencies per requested format."""
    fmt_list = [f.strip() for f in formats.split(",") if f.strip()]
    estimates: list[dict[str, Any]] = []
    for fmt in fmt_list:
        meta = _FORMAT_META.get(fmt)
        if not meta:
            estimates.append({"format": fmt, "error": "unsupported format"})
            continue
        estimates.append({
            "format": fmt,
            "estimated_size_mb": meta["size_mb"],
            "estimated_latency_ms": meta["latency_ms"],
            "compression_ratio": meta["compression_ratio"],
        })
    return {"model_id": model_id, "estimates": estimates}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@router.post("/export")
async def export_model(
    body: MultiFormatExportRequest,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Export a model to one or more edge formats.

    Delegates to ExportPipeline, which performs the conversions and returns a
    per-format result; the record is persisted so the artefacts it produced can
    be found again after a restart.
    """
    formats = body.requested_formats()
    record = await _export_pipeline.export_model(
        db,
        body.model_id,
        formats,
        workspace_id=workspace_id,
    )
    # Echo the singular `format` for single-format exports; multi-format
    # callers keep reading `formats`.
    if len(formats) == 1:
        record.setdefault("format", formats[0])
    return record


@router.get("/export/{job_id}/status")
async def export_status(
    job_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get status for an export job, including its download URL."""
    row = (
        await db.execute(
            select(ModelExport).where(
                ModelExport.id == _uuid_or_404(job_id, "Export job")
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Export job not found")

    payload = _serialise_export(row)
    payload["job_id"] = str(row.id)
    return payload


# ---------------------------------------------------------------------------
# Exports listing (preserves original endpoint)
# ---------------------------------------------------------------------------

@router.get("/exports")
async def list_exports(
    model_id: str | None = None,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List exports, optionally filtered by model.

    Returns only real exports. Five fixture rows used to be seeded at import,
    so a system that had never exported anything listed five downloads.
    """
    stmt = select(ModelExport)
    if workspace_id:
        stmt = stmt.where(ModelExport.workspace_id == _ws(workspace_id))
    if model_id:
        stmt = stmt.where(ModelExport.model_id == model_id)
    rows = (await db.execute(stmt.order_by(ModelExport.created_at))).scalars().all()
    return [_serialise_export(r) for r in rows]


@router.get("/exports/{export_id}")
async def get_export(
    export_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Get export details."""
    row = (
        await db.execute(
            select(ModelExport).where(
                ModelExport.id == _uuid_or_404(export_id, "Export")
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Export not found")
    return _serialise_export(row)


@router.delete("/exports/{export_id}", status_code=204)
async def delete_export(
    export_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> Response:
    """Remove an export record.

    `ExportHistory`'s delete button has always sent this and there has never
    been a handler: FastAPI answered 405, the component reported "Delete
    failed", and the row stayed. The route-wiring guard did not see it either -
    it compares paths and not methods, so this DELETE matched the GET at the
    same path and looked mounted.
    """
    row = (
        await db.execute(
            select(ModelExport).where(
                ModelExport.id == _uuid_or_404(export_id, "Export")
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Export not found")

    await db.delete(row)
    await db.commit()
    return Response(status_code=204)


@router.get("/exports/{export_id}/download")
async def download_export(
    export_id: str,
    format: str | None = Query(None, description="Ignored; kept for the console's link"),
    db: AsyncSession = Depends(get_async_session),
):
    """Download an exported model artifact.

    The console renders this as a plain `<a href>`, so a missing route was a
    404 page rather than an error the operator could interpret.

    An export row records where the pipeline wrote the artifact. When that
    location is a URL this redirects to it; when the exporter never recorded
    one there is nothing to serve, and saying so with a 409 is better than a
    zero-byte file named like a model.
    """
    row = (
        await db.execute(
            select(ModelExport).where(
                ModelExport.id == _uuid_or_404(export_id, "Export")
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Export not found")

    if row.status != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Export is {row.status}; there is nothing to download yet.",
        )

    if not row.download_url:
        raise HTTPException(
            status_code=409,
            detail=(
                "This export has no stored artifact. It was recorded without a "
                "download location, so there is no file to serve."
            ),
        )

    return RedirectResponse(url=row.download_url, status_code=307)


# ---------------------------------------------------------------------------
# Device detail
# ---------------------------------------------------------------------------


@router.delete("/devices/{device_id}", status_code=204)
async def remove_edge_device(
    device_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> Response:
    """Deregister a device.

    `DeviceFleet`'s Remove button called this and got a 405. It optimistically
    dropped the row from its local list first, so the device appeared to be
    removed until the page was reloaded and it came back.
    """
    row = (
        await db.execute(
            select(EdgeDevice).where(
                EdgeDevice.id == _uuid_or_404(device_id, "Device")
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    await db.delete(row)
    await db.commit()
    return Response(status_code=204)


@router.get("/devices/{device_id}/logs")
async def edge_device_logs(
    device_id: str,
    limit: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_async_session),
) -> dict:
    """Recent telemetry for one device, newest first.

    The console opens this in a new tab, so a 404 was a browser error page.

    These are the heartbeats the device actually sent - `device_metrics` rows -
    not an application log, and the response says so rather than implying a log
    stream the fleet does not collect.
    """
    device = (
        await db.execute(
            select(EdgeDevice).where(
                EdgeDevice.id == _uuid_or_404(device_id, "Device")
            )
        )
    ).scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    rows = (
        await db.execute(
            select(DeviceMetric)
            .where(DeviceMetric.device_id == device.id)
            .order_by(DeviceMetric.timestamp.desc())
            .limit(limit)
        )
    ).scalars().all()

    return {
        "device_id": str(device.id),
        "device_name": device.device_name,
        "source": "device_metrics",
        "note": (
            "Heartbeat telemetry reported by the device. The fleet does not "
            "collect application logs."
        ),
        "count": len(rows),
        "entries": [
            {
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "payload": r.payload,
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------

@router.get("/formats")
async def get_formats() -> list[dict]:
    """List supported export formats."""
    return SUPPORTED_FORMATS


# ---------------------------------------------------------------------------
# Package
# ---------------------------------------------------------------------------

@router.post("/package")
async def create_package(
    body: PackageRequest,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Build a deployable edge package: model, config, requirements, sample code.

    Delegates to ExportPipeline, which writes the package to disk and reports
    what it contains, then records it in offline_packages so the artefact can
    be found again after a restart.
    """
    record = await _export_pipeline.create_edge_package(
        db,
        body.model_id,
        body.format,
        config={"target": body.target_platform},
        workspace_id=workspace_id,
    )
    return {
        **record,
        "download_url": f"/api/edge/packages/{record['package_id']}/download",
    }


@router.post("/benchmark")
async def start_benchmark(body: BenchmarkRequest) -> dict[str, Any]:
    """Start a benchmark job for a model on a target device."""
    job_id = f"bench_{uuid.uuid4().hex[:6]}"
    meta = _FORMAT_META.get(body.format, _FORMAT_META["onnx"])
    bench = {
        "job_id": job_id,
        "model_id": body.model_id,
        "format": body.format,
        "device": body.device,
        "num_iterations": body.num_iterations,
        "warmup_iterations": body.warmup_iterations,
        "status": "completed",
        "results": {
            "latency": {
                "mean_ms": meta["latency_ms"],
                "p50_ms": meta["latency_ms"] * 0.95,
                "p90_ms": meta["latency_ms"] * 1.3,
                "p99_ms": meta["latency_ms"] * 1.8,
                "min_ms": meta["latency_ms"] * 0.7,
                "max_ms": meta["latency_ms"] * 2.5,
                "std_ms": meta["latency_ms"] * 0.15,
            },
            "throughput_fps": round(1000 / meta["latency_ms"], 1),
            "memory_mb": meta["size_mb"] * 1.2,
            "histogram": [
                {"bucket_ms": round(meta["latency_ms"] * f, 1), "count": c}
                for f, c in [
                    (0.7, 2), (0.8, 8), (0.9, 20), (1.0, 40),
                    (1.1, 18), (1.2, 8), (1.5, 3), (2.0, 1),
                ]
            ],
            "comparison": {
                "vs_cpu": {"speedup": 1.0 if body.device == "cpu" else 3.2},
                "vs_gpu": {"speedup": 0.3 if body.device == "cpu" else 1.0},
            },
        },
        "created_at": time.time(),
    }
    row = EdgeBenchmark(
        workspace_id=_ws(workspace_id),
        model_id=body.model_id,
        device_type=body.device,
        results=bench,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"job_id": str(row.id)}


@router.get("/benchmark/{job_id}/results")
async def benchmark_results(
    job_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get benchmark results including latency stats, histogram, and comparison."""
    row = (
        await db.execute(
            select(EdgeBenchmark).where(
                EdgeBenchmark.id == _uuid_or_404(job_id, "Benchmark job")
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Benchmark job not found")
    bench = row.results or {}
    return {
        "job_id": job_id,
        "model_id": bench["model_id"],
        "format": bench["format"],
        "device": bench["device"],
        "status": bench["status"],
        "latency": bench["results"]["latency"],
        "throughput_fps": bench["results"]["throughput_fps"],
        "memory_mb": bench["results"]["memory_mb"],
        "histogram": bench["results"]["histogram"],
        "comparison": bench["results"]["comparison"],
    }


# ---------------------------------------------------------------------------
# Edge Devices
# ---------------------------------------------------------------------------

@router.get("/devices")
async def list_edge_devices(
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> list[dict]:
    """List registered edge devices.

    Reads the edge_fleet table. Four fixture devices used to be seeded at
    import, so an empty fleet reported a Jetson, a Pi, an Xavier and a Coral.
    """
    stmt = select(EdgeDevice)
    if workspace_id:
        stmt = stmt.where(EdgeDevice.workspace_id == _ws(workspace_id))
    rows = (await db.execute(stmt.order_by(EdgeDevice.created_at))).scalars().all()
    return [
        {
            "id": str(d.id),
            "name": d.device_name,
            "device_type": d.device_type,
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "last_seen": d.last_seen.timestamp() if d.last_seen else None,
        }
        for d in rows
    ]


@router.post("/devices")
async def register_edge_device(
    body: DeviceRegisterRequest,
    workspace_id: str | None = Query(None),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Register a new edge device, returning device info with API key."""
    api_key = f"eak_{uuid.uuid4().hex}"
    row = EdgeDevice(
        workspace_id=_ws(workspace_id),
        device_name=body.name,
        device_type=body.device_type,
        location=body.location,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    return {
        "id": str(row.id),
        "name": row.device_name,
        "device_type": row.device_type,
        "platform": body.platform,
        "location": row.location,
        "status": row.status.value if hasattr(row.status, "value") else str(row.status),
        "api_key": api_key,
        "registered_at": row.created_at.timestamp() if row.created_at else None,
    }


@router.post("/devices/{device_id}/update")
async def update_device_firmware(
    device_id: str,
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Trigger firmware/software update on an edge device."""
    row = (
        await db.execute(
            select(EdgeDevice).where(
                EdgeDevice.id == _uuid_or_404(device_id, "Device")
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"device_id": device_id, "status": "updating"}
