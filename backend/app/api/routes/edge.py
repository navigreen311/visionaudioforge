"""Edge Deployment routes — export, packaging, benchmarking, device management."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/edge", tags=["edge"])


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
    optimize: bool = True
    quantize: bool = False


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


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------
_exports: dict[str, dict] = {}
_benchmarks: dict[str, dict] = {}
_packages: dict[str, dict] = {}
_edge_devices: dict[str, dict] = {}

SUPPORTED_FORMATS = [
    {"name": "onnx", "description": "Open Neural Network Exchange", "extensions": [".onnx"]},
    {"name": "tensorrt", "description": "NVIDIA TensorRT", "extensions": [".engine"]},
    {"name": "tflite", "description": "TensorFlow Lite", "extensions": [".tflite"]},
    {"name": "coreml", "description": "Apple Core ML", "extensions": [".mlmodel"]},
    {"name": "openvino", "description": "Intel OpenVINO", "extensions": [".xml", ".bin"]},
]

# Format metadata for estimates
_FORMAT_META = {
    "onnx": {"size_mb": 42.5, "latency_ms": 12.3, "compression_ratio": 1.0},
    "tensorrt": {"size_mb": 38.1, "latency_ms": 4.7, "compression_ratio": 0.90},
    "tflite": {"size_mb": 11.2, "latency_ms": 18.9, "compression_ratio": 0.26},
    "coreml": {"size_mb": 40.0, "latency_ms": 8.1, "compression_ratio": 0.94},
    "openvino": {"size_mb": 35.6, "latency_ms": 6.2, "compression_ratio": 0.84},
}

# Seed 5 mock past exports
_MOCK_EXPORTS = [
    {
        "id": f"export_{i:03d}",
        "model_id": f"model_{(i % 3) + 1}",
        "format": ["onnx", "tensorrt", "tflite", "coreml", "openvino"][i % 5],
        "status": "completed",
        "file_size_mb": [42.5, 38.1, 11.2, 40.0, 35.6][i % 5],
        "download_url": f"https://storage.example.com/exports/export_{i:03d}.zip",
        "created_at": 1711000000 + i * 3600,
    }
    for i in range(5)
]
for _e in _MOCK_EXPORTS:
    _exports[_e["id"]] = _e

# Seed 4 mock edge devices
_MOCK_DEVICES = [
    {
        "id": "dev_001",
        "name": "Jetson-Nano-Lab1",
        "device_type": "nvidia-jetson-nano",
        "platform": "linux-arm64",
        "status": "online",
        "firmware_version": "4.6.1",
        "last_seen": 1711000000,
    },
    {
        "id": "dev_002",
        "name": "RPi4-Warehouse",
        "device_type": "raspberry-pi-4",
        "platform": "linux-arm64",
        "status": "online",
        "firmware_version": "3.2.0",
        "last_seen": 1711000000,
    },
    {
        "id": "dev_003",
        "name": "Xavier-AGX-Floor2",
        "device_type": "nvidia-xavier-agx",
        "platform": "linux-arm64",
        "status": "offline",
        "firmware_version": "5.0.2",
        "last_seen": 1710900000,
    },
    {
        "id": "dev_004",
        "name": "Coral-EdgeTPU-Gate",
        "device_type": "google-coral",
        "platform": "linux-arm64",
        "status": "online",
        "firmware_version": "2.1.0",
        "last_seen": 1711000000,
    },
]
for _d in _MOCK_DEVICES:
    _edge_devices[_d["id"]] = _d


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
async def export_model(body: ExportRequest) -> dict[str, Any]:
    """Start an export job for a model to an edge-optimized format."""
    job_id = f"export_{uuid.uuid4().hex[:6]}"
    export = {
        "id": job_id,
        "model_id": body.model_id,
        "format": body.format,
        "optimize": body.optimize,
        "quantize": body.quantize,
        "status": "completed",
        "file_size_mb": _FORMAT_META.get(body.format, {}).get("size_mb", 42.5),
        "download_url": f"https://storage.example.com/exports/{job_id}.zip",
        "created_at": time.time(),
    }
    _exports[job_id] = export
    return {"job_id": job_id}


@router.get("/export/{job_id}/status")
async def export_status(job_id: str) -> dict[str, Any]:
    """Get per-format status for an export job, including download URLs."""
    if job_id not in _exports:
        raise HTTPException(status_code=404, detail="Export job not found")
    exp = _exports[job_id]
    return {
        "job_id": job_id,
        "model_id": exp["model_id"],
        "status": exp["status"],
        "format": exp["format"],
        "file_size_mb": exp.get("file_size_mb"),
        "download_url": exp.get("download_url", f"https://storage.example.com/exports/{job_id}.zip"),
        "created_at": exp.get("created_at"),
    }


# ---------------------------------------------------------------------------
# Exports listing (preserves original endpoint)
# ---------------------------------------------------------------------------

@router.get("/exports")
async def list_exports(model_id: str | None = None) -> list[dict]:
    """List all exports, optionally filtered by model."""
    exports = list(_exports.values())
    if model_id:
        exports = [e for e in exports if e["model_id"] == model_id]
    return exports


@router.get("/exports/{export_id}")
async def get_export(export_id: str) -> dict:
    """Get export details."""
    if export_id not in _exports:
        raise HTTPException(status_code=404, detail="Export not found")
    return _exports[export_id]


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
async def create_package(body: PackageRequest) -> dict[str, Any]:
    """Package a model with runtime for edge deployment."""
    package_id = f"pkg_{uuid.uuid4().hex[:6]}"
    contents = [
        {"name": f"model.{body.format}", "size_bytes": 44_564_480},
        {"name": "runtime.so", "size_bytes": 8_192_000},
        {"name": "config.json", "size_bytes": 1_024},
        {"name": "labels.txt", "size_bytes": 512},
    ]
    if not body.include_runtime:
        contents = [c for c in contents if c["name"] != "runtime.so"]
    pkg = {
        "package_id": package_id,
        "model_id": body.model_id,
        "format": body.format,
        "target_platform": body.target_platform,
        "contents": contents,
        "total_size_bytes": sum(c["size_bytes"] for c in contents),
        "download_url": f"https://storage.example.com/packages/{package_id}.tar.gz",
        "created_at": time.time(),
    }
    _packages[package_id] = pkg
    return {
        "package_id": package_id,
        "contents": contents,
        "download_url": pkg["download_url"],
    }


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

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
    _benchmarks[job_id] = bench
    return {"job_id": job_id}


@router.get("/benchmark/{job_id}/results")
async def benchmark_results(job_id: str) -> dict[str, Any]:
    """Get benchmark results including latency stats, histogram, and comparison."""
    if job_id not in _benchmarks:
        raise HTTPException(status_code=404, detail="Benchmark job not found")
    bench = _benchmarks[job_id]
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
async def list_edge_devices() -> list[dict]:
    """List all registered edge devices with status and version."""
    return list(_edge_devices.values())


@router.post("/devices")
async def register_edge_device(body: DeviceRegisterRequest) -> dict[str, Any]:
    """Register a new edge device, returning device info with API key."""
    device_id = f"dev_{uuid.uuid4().hex[:6]}"
    api_key = f"eak_{uuid.uuid4().hex}"
    device = {
        "id": device_id,
        "name": body.name,
        "device_type": body.device_type,
        "platform": body.platform,
        "location": body.location,
        "status": "online",
        "firmware_version": "1.0.0",
        "api_key": api_key,
        "registered_at": time.time(),
        "last_seen": time.time(),
    }
    _edge_devices[device_id] = device
    return device


@router.post("/devices/{device_id}/update")
async def update_device_firmware(device_id: str) -> dict[str, Any]:
    """Trigger firmware/software update on an edge device."""
    if device_id not in _edge_devices:
        raise HTTPException(status_code=404, detail="Device not found")
    _edge_devices[device_id]["status"] = "updating"
    return {"device_id": device_id, "status": "updating"}
