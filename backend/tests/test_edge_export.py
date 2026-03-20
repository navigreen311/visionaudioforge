"""Tests for the Edge Export pipeline — ONNX export, converters, pipeline,
and API routes."""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Optional imports — tests skip gracefully when deps are missing
# ---------------------------------------------------------------------------

torch = pytest.importorskip("torch")
import torch.nn as nn  # noqa: E402

from app.services.edge.onnx_export import ONNXExporter  # noqa: E402
from app.services.edge.converters import ModelConverter  # noqa: E402
from app.services.edge.export_pipeline import ExportPipeline  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_model():
    """A trivial linear model for export tests."""
    return nn.Sequential(nn.Linear(10, 32), nn.ReLU(), nn.Linear(32, 5))


@pytest.fixture
def exporter():
    return ONNXExporter()


@pytest.fixture
def converter():
    return ModelConverter()


@pytest.fixture
def pipeline():
    return ExportPipeline()


@pytest.fixture
def onnx_file(simple_model, exporter, tmp_path):
    """Export a simple model and return the ONNX file path."""
    path = str(tmp_path / "test_model.onnx")
    exporter.export_to_onnx(simple_model, (1, 10), path)
    return path


# ---------------------------------------------------------------------------
# ONNX Export tests
# ---------------------------------------------------------------------------

class TestONNXExport:
    def test_onnx_export_creates_file(self, simple_model, exporter, tmp_path):
        path = str(tmp_path / "model.onnx")
        result = exporter.export_to_onnx(simple_model, (1, 10), path)

        assert os.path.exists(path)
        assert result["path"] == path
        assert result["size_mb"] > 0
        assert result["opset"] == 13
        assert "input" in result["input_names"]
        assert "output" in result["output_names"]

    def test_onnx_validation(self, exporter, onnx_file):
        result = exporter.validate_onnx(onnx_file)

        assert result["valid"] is True
        assert result["node_count"] > 0
        assert result["opset"] >= 13
        assert len(result["inputs"]) > 0
        assert len(result["outputs"]) > 0

    def test_onnx_optimization(self, exporter, onnx_file):
        result = exporter.optimize_onnx(onnx_file)

        assert os.path.exists(result["path"])
        assert result["original_size_mb"] > 0
        assert result["optimized_size_mb"] > 0
        assert "reduction_pct" in result

    def test_onnx_benchmark(self, exporter, onnx_file):
        result = exporter.benchmark_onnx(onnx_file, iterations=10)

        assert "avg_ms" in result
        assert "p95_ms" in result
        assert "throughput_per_s" in result
        assert result["avg_ms"] >= 0
        assert result["throughput_per_s"] >= 0


# ---------------------------------------------------------------------------
# Converter tests
# ---------------------------------------------------------------------------

class TestConverters:
    def test_converter_stubs_return_instructions(self, converter, onnx_file):
        results = {
            "tensorrt": converter.to_tensorrt_stub(onnx_file),
            "openvino": converter.to_openvino_stub(onnx_file),
            "coreml": converter.to_coreml_stub(onnx_file),
            "tflite": converter.to_tflite_stub(onnx_file),
            "webgpu": converter.to_webgpu_stub(onnx_file),
        }

        for fmt, result in results.items():
            assert result["status"] == "stub", f"{fmt} should return stub"
            assert "note" in result, f"{fmt} should have a note"
            assert result["source_model"] == onnx_file

    def test_supported_formats_list(self, converter):
        formats = converter.get_supported_formats()

        assert len(formats) == 6
        names = [f["format"] for f in formats]
        assert "onnx" in names
        assert "tensorrt" in names
        assert "openvino" in names
        assert "coreml" in names
        assert "tflite" in names
        assert "webgpu" in names

        onnx_fmt = next(f for f in formats if f["format"] == "onnx")
        assert onnx_fmt["available"] is True
        assert "requirements" in onnx_fmt
        assert "platforms" in onnx_fmt


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------

class TestExportPipeline:
    @pytest.mark.asyncio
    async def test_export_pipeline_multiple_formats(self, pipeline):
        result = await pipeline.export_model(
            db=None,
            model_id="test-model",
            formats=["onnx", "tensorrt", "openvino"],
            optimization_level="basic",
        )

        assert result["status"] == "completed"
        assert "onnx" in result["exports"]
        assert "tensorrt" in result["exports"]
        assert "openvino" in result["exports"]
        assert result["exports"]["tensorrt"]["status"] == "stub"
        assert result["total_size_mb"] >= 0

    @pytest.mark.asyncio
    async def test_edge_package_includes_files(self, pipeline):
        result = await pipeline.create_edge_package(
            db=None, model_id="test-model", fmt="onnx"
        )

        assert "package_id" in result
        assert result["format"] == "onnx"
        assert "config.json" in result["includes"]
        assert "requirements.txt" in result["includes"]
        assert "inference.py" in result["includes"]
        assert "model.onnx" in result["includes"]

    @pytest.mark.asyncio
    async def test_inference_code_generation(self, pipeline):
        for fmt in ["onnx", "tensorrt", "openvino", "coreml", "tflite", "webgpu"]:
            code = await pipeline.generate_inference_code(
                fmt, {"input_shape": [1, 10]}
            )
            assert len(code) > 50, f"{fmt} code should be non-trivial"
            assert isinstance(code, str)


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------

class TestEdgeAPI:
    @pytest.fixture
    def client(self):
        """Create a test client with edge routes."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.routes.edge import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_api_export(self, client):
        resp = client.post(
            "/api/edge/export",
            json={"model_id": "test", "formats": ["onnx"], "optimization_level": "basic"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "exports" in data
        assert "onnx" in data["exports"]

    def test_api_formats(self, client):
        resp = client.get("/api/edge/formats")
        assert resp.status_code == 200
        formats = resp.json()
        assert len(formats) == 6
        assert any(f["format"] == "onnx" for f in formats)

    def test_api_package(self, client):
        resp = client.post(
            "/api/edge/package",
            json={"model_id": "test", "format": "onnx"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "package_id" in data
        assert "includes" in data
        assert "inference.py" in data["includes"]

    def test_api_list_exports(self, client):
        # First create an export
        client.post(
            "/api/edge/export",
            json={"model_id": "test", "formats": ["onnx"]},
        )
        resp = client.get("/api/edge/exports")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_api_export_details(self, client):
        # Create an export
        create_resp = client.post(
            "/api/edge/export",
            json={"model_id": "test", "formats": ["onnx"]},
        )
        export_id = create_resp.json()["export_id"]

        resp = client.get(f"/api/edge/exports/{export_id}")
        assert resp.status_code == 200
        assert resp.json()["export_id"] == export_id

    def test_api_export_not_found(self, client):
        resp = client.get("/api/edge/exports/nonexistent-id")
        assert resp.status_code == 404
