"""Offline package builder — create deployable bundles for edge devices.

Backed by the ``offline_packages`` table: a built package is an artifact
operators come back to days later, so its manifest and checksum must survive
a restart.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.edge_fleet import OfflinePackage

# Model format mapping by device type
_DEVICE_FORMAT_MAP: dict[str, str] = {
    "jetson_nano": "TensorRT",
    "jetson_xavier": "TensorRT",
    "raspberry_pi": "TFLite",
    "x86_server": "ONNX",
    "mobile": "TFLite",
    "browser": "WebGPU",
}

_EXT_MAP: dict[str, str] = {
    "TensorRT": ".engine",
    "TFLite": ".tflite",
    "ONNX": ".onnx",
    "WebGPU": ".wgsl",
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _as_uuid(value) -> uuid.UUID | None:
    if value is None:
        return None
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


class OfflinePackageBuilder:
    """Builds self-contained offline deployment packages for edge devices."""

    async def build_package(
        self,
        db: AsyncSession,
        model_id: str,
        device_type: str,
        include_runtime: bool = True,
        workspace_id: str | None = None,
    ) -> dict:
        """Build an offline deployment package for a model and device type."""
        model_format = _DEVICE_FORMAT_MAP.get(device_type, "ONNX")
        model_ext = _EXT_MAP.get(model_format, ".bin")
        package_id = uuid.uuid4()

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
        checksum = hashlib.sha256(
            f"{package_id}-{model_id}-{device_type}".encode()
        ).hexdigest()

        instructions = (
            f"1. Extract package to target device\n"
            f"2. Run: bash setup.sh\n"
            f"3. Configure: edit config.json\n"
            f"4. Start inference: python inference_runner.py\n"
            f"Model format: {model_format} (optimized for {device_type})"
        )

        package = OfflinePackage(
            id=package_id,
            workspace_id=_as_uuid(workspace_id),
            model_id=model_id,
            device_type=device_type,
            model_format=model_format,
            size_mb=total_size,
            contents=contents,
            instructions=instructions,
            checksum=checksum,
        )
        db.add(package)
        await db.commit()

        return {
            "package_id": str(package_id),
            "size_mb": total_size,
            "contents": contents,
            "instructions": instructions,
        }

    async def list_packages(
        self, db: AsyncSession, workspace_id: str | None = None
    ) -> list[dict]:
        """List packages, scoped to a workspace when one is given."""
        query = select(OfflinePackage)
        if workspace_id is not None:
            query = query.where(OfflinePackage.workspace_id == _as_uuid(workspace_id))

        result = await db.execute(query.order_by(OfflinePackage.created_at))
        return [
            {
                "package_id": str(p.id),
                "model_id": p.model_id,
                "device_type": p.device_type,
                "model_format": p.model_format,
                "size_mb": p.size_mb,
                "created_at": _iso(p.created_at),
            }
            for p in result.scalars().all()
        ]

    async def get_package_manifest(
        self, db: AsyncSession, package_id: str
    ) -> dict:
        """Return a package's file listing, total size and checksum."""
        try:
            key = _as_uuid(package_id)
        except (ValueError, AttributeError, TypeError):
            raise KeyError(f"Package {package_id} not found")

        result = await db.execute(
            select(OfflinePackage).where(OfflinePackage.id == key)
        )
        package = result.scalar_one_or_none()
        if package is None:
            raise KeyError(f"Package {package_id} not found")

        return {
            "files": package.contents,
            "total_size_mb": package.size_mb,
            "checksum": package.checksum,
        }
