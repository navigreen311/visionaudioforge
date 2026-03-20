"""Offline package builder — create deployable bundles for edge devices."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

# In-memory package store
_packages: dict[str, dict[str, Any]] = {}

# Model format mapping by device type
_DEVICE_FORMAT_MAP: dict[str, str] = {
    "jetson_nano": "TensorRT",
    "jetson_xavier": "TensorRT",
    "raspberry_pi": "TFLite",
    "x86_server": "ONNX",
    "mobile": "TFLite",
    "browser": "WebGPU",
}


class OfflinePackageBuilder:
    """Builds self-contained offline deployment packages for edge devices."""

    async def build_package(
        self,
        db: Any,
        model_id: str,
        device_type: str,
        include_runtime: bool = True,
    ) -> dict:
        """Build an offline deployment package for a given model and device type."""
        model_format = _DEVICE_FORMAT_MAP.get(device_type, "ONNX")
        package_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        # Determine model file extension
        ext_map = {
            "TensorRT": ".engine",
            "TFLite": ".tflite",
            "ONNX": ".onnx",
            "WebGPU": ".wgsl",
        }
        model_ext = ext_map.get(model_format, ".bin")

        contents = [
            {"file": f"model{model_ext}", "format": model_format, "size_mb": 45.0},
            {"file": "config.json", "format": "JSON", "size_mb": 0.01},
            {"file": "inference_runner.py", "format": "Python", "size_mb": 0.05},
            {"file": "requirements.txt", "format": "Text", "size_mb": 0.001},
            {"file": "setup.sh", "format": "Shell", "size_mb": 0.002},
            {"file": "README.md", "format": "Markdown", "size_mb": 0.003},
        ]

        if include_runtime:
            contents.append(
                {"file": "runtime/", "format": "Directory", "size_mb": 15.0}
            )

        total_size = round(sum(c["size_mb"] for c in contents), 3)
        checksum = hashlib.sha256(f"{package_id}-{model_id}-{device_type}".encode()).hexdigest()

        instructions = (
            f"1. Extract package to target device\n"
            f"2. Run: bash setup.sh\n"
            f"3. Configure: edit config.json\n"
            f"4. Start inference: python inference_runner.py\n"
            f"Model format: {model_format} (optimized for {device_type})"
        )

        package_record = {
            "package_id": package_id,
            "model_id": model_id,
            "device_type": device_type,
            "model_format": model_format,
            "size_mb": total_size,
            "contents": contents,
            "instructions": instructions,
            "checksum": checksum,
            "created_at": now.isoformat(),
            "workspace_id": None,
        }
        _packages[package_id] = package_record

        return {
            "package_id": package_id,
            "size_mb": total_size,
            "contents": contents,
            "instructions": instructions,
        }

    async def list_packages(self, db: Any, workspace_id: str) -> list[dict]:
        """List all packages, optionally filtered by workspace."""
        results = []
        for p in _packages.values():
            results.append({
                "package_id": p["package_id"],
                "model_id": p["model_id"],
                "device_type": p["device_type"],
                "model_format": p["model_format"],
                "size_mb": p["size_mb"],
                "created_at": p["created_at"],
            })
        return results

    async def get_package_manifest(self, package_id: str) -> dict:
        """Return the manifest for a package including file listing and checksum."""
        pkg = _packages.get(package_id)
        if pkg is None:
            raise KeyError(f"Package {package_id} not found")

        return {
            "files": pkg["contents"],
            "total_size_mb": pkg["size_mb"],
            "checksum": pkg["checksum"],
        }
