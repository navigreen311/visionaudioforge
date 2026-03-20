"""Format converters — stub implementations for TensorRT, OpenVINO, CoreML,
TFLite, and WebGPU.  Real conversions require platform-specific libraries;
these stubs return instructions and metadata."""

from __future__ import annotations


class ModelConverter:
    """Convert ONNX models to various edge-deployment formats."""

    # ------------------------------------------------------------------
    # Stub converters
    # ------------------------------------------------------------------

    def to_tensorrt_stub(self, onnx_path: str) -> dict:
        return {
            "status": "stub",
            "note": (
                "TensorRT requires NVIDIA GPU + tensorrt package. "
                "Install: pip install tensorrt"
            ),
            "estimated_speedup": "2-5x",
            "source_model": onnx_path,
        }

    def to_openvino_stub(self, onnx_path: str) -> dict:
        return {
            "status": "stub",
            "note": (
                "OpenVINO requires: pip install openvino. "
                "Enables Intel CPU/GPU optimization."
            ),
            "command": "mo --input_model model.onnx --output_dir openvino_model/",
            "source_model": onnx_path,
        }

    def to_coreml_stub(self, onnx_path: str) -> dict:
        return {
            "status": "stub",
            "note": (
                "CoreML requires macOS + coremltools. "
                "Install: pip install coremltools"
            ),
            "command": "ct.convert(onnx_model)",
            "source_model": onnx_path,
        }

    def to_tflite_stub(self, onnx_path: str) -> dict:
        return {
            "status": "stub",
            "note": (
                "TFLite requires: pip install tensorflow. "
                "Use tf.lite.TFLiteConverter."
            ),
            "quantization_options": ["float32", "float16", "int8"],
            "source_model": onnx_path,
        }

    def to_webgpu_stub(self, onnx_path: str) -> dict:
        return {
            "status": "stub",
            "note": (
                "WebGPU inference via ONNX Runtime Web. "
                "Export ONNX model, load in browser with ort.InferenceSession."
            ),
            "source_model": onnx_path,
        }

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def get_supported_formats(self) -> list[dict]:
        """Return metadata about every supported export format."""
        return [
            {
                "format": "onnx",
                "available": True,
                "requirements": "pip install torch onnx",
                "platforms": ["linux", "windows", "macos"],
            },
            {
                "format": "tensorrt",
                "available": False,
                "requirements": "pip install tensorrt (NVIDIA GPU required)",
                "platforms": ["linux", "windows"],
            },
            {
                "format": "openvino",
                "available": False,
                "requirements": "pip install openvino",
                "platforms": ["linux", "windows", "macos"],
            },
            {
                "format": "coreml",
                "available": False,
                "requirements": "pip install coremltools (macOS required)",
                "platforms": ["macos"],
            },
            {
                "format": "tflite",
                "available": False,
                "requirements": "pip install tensorflow",
                "platforms": ["linux", "windows", "macos", "android"],
            },
            {
                "format": "webgpu",
                "available": False,
                "requirements": "ONNX Runtime Web (browser-based)",
                "platforms": ["web"],
            },
        ]
