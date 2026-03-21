"""Edge Export routes — ONNX export, format listing, export management,
package generation, and inference benchmarking."""

from __future__ import annotations

import random
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


class PackageRequest(BaseModel):
    model_id: str
    format: str = Field("onnx", pattern="^(onnx|tensorrt|tflite|coreml|openvino)$")


class BenchmarkRequest(BaseModel):
    model_id: str
    format: str = Field("onnx", pattern="^(onnx|tensorrt|tflite|coreml|openvino)$")
    input_shape: str = "1,3,224,224"
    iterations: int = Field(100, ge=1, le=10000)
    warmup: int = Field(10, ge=0, le=1000)
    device: str = Field("cpu", pattern="^(cpu|gpu|auto)$")


# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------
_exports: dict[str, dict[str, Any]] = {}
_packages: dict[str, dict[str, Any]] = {}
_benchmarks: dict[str, dict[str, Any]] = {}

SUPPORTED_FORMATS = [
    {"name": "onnx", "description": "Open Neural Network Exchange", "extensions": [".onnx"]},
    {"name": "tensorrt", "description": "NVIDIA TensorRT", "extensions": [".engine"]},
    {"name": "tflite", "description": "TensorFlow Lite", "extensions": [".tflite"]},
    {"name": "coreml", "description": "Apple Core ML", "extensions": [".mlmodel"]},
    {"name": "openvino", "description": "Intel OpenVINO", "extensions": [".xml", ".bin"]},
]

_INFERENCE_CODE_TEMPLATE = '''\
import onnxruntime as ort
import numpy as np


def load_model(model_path: str) -> ort.InferenceSession:
    """Load the ONNX model for inference."""
    providers = ["CPUExecutionProvider"]
    return ort.InferenceSession(model_path, providers=providers)


def preprocess(image: np.ndarray) -> np.ndarray:
    """Normalize and reshape input for the model."""
    img = image.astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    img = (img - mean) / std
    return np.transpose(img, (2, 0, 1))[np.newaxis, ...]


def predict(session: ort.InferenceSession, input_data: np.ndarray):
    """Run inference and return predictions."""
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_data})
    return outputs[0]


if __name__ == "__main__":
    session = load_model("model.onnx")
    dummy = np.random.randn(1, 3, 224, 224).astype(np.float32)
    result = predict(session, dummy)
    print("Output shape:", result.shape)
'''


# ---------------------------------------------------------------------------
# Export endpoints
# ---------------------------------------------------------------------------

@router.post("/export")
async def export_model(body: ExportRequest) -> dict[str, Any]:
    """Export a model to edge-optimized format."""
    export_id = str(uuid.uuid4())
    export: dict[str, Any] = {
        "id": export_id,
        "model_id": body.model_id,
        "format": body.format,
        "optimize": body.optimize,
        "quantize": body.quantize,
        "status": "completed",
        "file_size_mb": 42.5,
        "created_at": time.time(),
    }
    _exports[export_id] = export
    return export


@router.get("/exports")
async def list_exports(model_id: str | None = None) -> list[dict[str, Any]]:
    """List all exports, optionally filtered by model."""
    exports = list(_exports.values())
    if model_id:
        exports = [e for e in exports if e["model_id"] == model_id]
    return exports


@router.get("/exports/{export_id}")
async def get_export(export_id: str) -> dict[str, Any]:
    """Get export details."""
    if export_id not in _exports:
        raise HTTPException(status_code=404, detail="Export not found")
    return _exports[export_id]


@router.get("/formats")
async def get_formats() -> list[dict[str, Any]]:
    """List supported export formats."""
    return SUPPORTED_FORMATS


# ---------------------------------------------------------------------------
# Package generation endpoints
# ---------------------------------------------------------------------------

@router.post("/package")
async def generate_package(body: PackageRequest) -> dict[str, Any]:
    """Generate a deployment-ready edge package (stub)."""
    package_id = str(uuid.uuid4())

    ext_map = {"onnx": ".onnx", "tensorrt": ".engine", "tflite": ".tflite",
               "coreml": ".mlmodel", "openvino": ".xml"}
    model_ext = ext_map.get(body.format, ".onnx")

    files = [
        {"name": f"model{model_ext}", "size_kb": 43520.0},
        {"name": "config.json", "size_kb": 2.1},
        {"name": "requirements.txt", "size_kb": 0.4},
        {"name": "inference.py", "size_kb": 1.8},
        {"name": "README.md", "size_kb": 3.2},
    ]

    total_size_mb = round(sum(f["size_kb"] for f in files) / 1024, 1)

    package: dict[str, Any] = {
        "package_id": package_id,
        "model_id": body.model_id,
        "format": body.format,
        "status": "completed",
        "files": files,
        "total_size_mb": total_size_mb,
        "inference_code": _INFERENCE_CODE_TEMPLATE,
        "download_url": f"/api/edge/package/{package_id}/download",
        "created_at": time.time(),
    }
    _packages[package_id] = package
    return package


# ---------------------------------------------------------------------------
# Benchmark endpoints
# ---------------------------------------------------------------------------

def _generate_latencies(iterations: int, base_ms: float) -> list[float]:
    """Generate realistic-looking latency samples with a right-skewed distribution."""
    return sorted(
        round(base_ms + random.gauss(0, base_ms * 0.15) + abs(random.gauss(0, base_ms * 0.05)), 3)
        for _ in range(iterations)
    )


def _percentile(sorted_data: list[float], p: float) -> float:
    """Compute the p-th percentile from sorted data."""
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return round(sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f]), 3)


@router.post("/benchmark")
async def run_benchmark(body: BenchmarkRequest) -> dict[str, Any]:
    """Run an inference benchmark (stub with simulated data)."""
    benchmark_id = str(uuid.uuid4())

    # Base latency varies by format and device
    base_map: dict[str, float] = {
        "onnx": 12.5, "tensorrt": 5.4, "tflite": 18.2,
        "coreml": 8.1, "openvino": 9.7,
    }
    base_ms = base_map.get(body.format, 12.5)
    if body.device == "gpu":
        base_ms *= 0.4

    latencies = _generate_latencies(body.iterations, base_ms)
    avg_ms = round(sum(latencies) / len(latencies), 3)
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)

    result: dict[str, Any] = {
        "benchmark_id": benchmark_id,
        "config": body.model_dump(),
        "summary": {
            "avg_ms": avg_ms,
            "p50_ms": p50,
            "p95_ms": p95,
            "p99_ms": p99,
            "throughput_fps": round(1000 / avg_ms, 1),
            "memory_mb": round(random.uniform(120, 380), 0),
            "speedup": f"{round(random.uniform(1.5, 3.5), 1)}x",
        },
        "latencies": latencies,
        "percentiles": {"p50": p50, "p95": p95, "p99": p99},
        "created_at": time.time(),
    }
    _benchmarks[benchmark_id] = result
    return result


@router.get("/benchmark/{benchmark_id}/results")
async def get_benchmark_results(benchmark_id: str) -> dict[str, Any]:
    """Retrieve stored benchmark results."""
    if benchmark_id not in _benchmarks:
        raise HTTPException(status_code=404, detail="Benchmark not found")
    return _benchmarks[benchmark_id]
