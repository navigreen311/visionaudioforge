"""Storage connectors — S3, local filesystem, and Google Drive stub."""

from __future__ import annotations

import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


# =====================================================================
# Base class
# =====================================================================


class BaseStorageConnector(ABC):
    """Abstract storage connector interface."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, **kwargs: Any) -> dict[str, Any]:
        """Upload *data* under *key*."""

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Download and return contents stored at *key*."""

    @abstractmethod
    async def list(self, prefix: str = "") -> list[str]:
        """List keys matching *prefix*."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete the object at *key*. Return *True* if it existed."""


# =====================================================================
# S3-compatible connector
# =====================================================================


class S3Connector(BaseStorageConnector):
    """Amazon S3 (or S3-compatible / MinIO) storage connector."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.bucket = config["bucket"]
        self.region = config.get("region", "us-east-1")
        self._access_key = config.get("access_key", "")
        self._secret_key = config.get("secret_key", "")
        self._endpoint_url = config.get("endpoint_url")

        try:
            import boto3  # type: ignore[import-untyped]

            kwargs: dict[str, Any] = {
                "service_name": "s3",
                "region_name": self.region,
                "aws_access_key_id": self._access_key,
                "aws_secret_access_key": self._secret_key,
            }
            if self._endpoint_url:
                kwargs["endpoint_url"] = self._endpoint_url
            self._client = boto3.client(**kwargs)
        except ImportError:
            self._client = None

    async def upload(self, key: str, data: bytes, **kwargs: Any) -> dict[str, Any]:
        if self._client is None:
            return {"ok": False, "error": "boto3 not installed"}
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data, **kwargs)
        return {"ok": True, "bucket": self.bucket, "key": key}

    async def download(self, key: str) -> bytes:
        if self._client is None:
            raise RuntimeError("boto3 not installed")
        resp = self._client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    async def list(self, prefix: str = "") -> list[str]:
        if self._client is None:
            return []
        resp = self._client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj["Key"] for obj in resp.get("Contents", [])]

    async def delete(self, key: str) -> bool:
        if self._client is None:
            return False
        self._client.delete_object(Bucket=self.bucket, Key=key)
        return True


# =====================================================================
# Local filesystem connector
# =====================================================================


class LocalConnector(BaseStorageConnector):
    """Local-filesystem storage connector for dev/testing."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.root = Path(config.get("root", "/tmp/vaf-storage"))
        self.root.mkdir(parents=True, exist_ok=True)

    async def upload(self, key: str, data: bytes, **_kwargs: Any) -> dict[str, Any]:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"ok": True, "path": str(path)}

    async def download(self, key: str) -> bytes:
        path = self.root / key
        if not path.exists():
            raise FileNotFoundError(f"Key not found: {key}")
        return path.read_bytes()

    async def list(self, prefix: str = "") -> list[str]:
        results: list[str] = []
        search_root = self.root / prefix if prefix else self.root
        if not search_root.exists():
            return results
        for p in search_root.rglob("*"):
            if p.is_file():
                results.append(str(p.relative_to(self.root)))
        return sorted(results)

    async def delete(self, key: str) -> bool:
        path = self.root / key
        if path.exists():
            path.unlink()
            return True
        return False


# =====================================================================
# Google Drive stub
# =====================================================================


class GoogleDriveStub(BaseStorageConnector):
    """Stub connector for Google Drive — returns setup instructions."""

    _NOTE = (
        "Google Drive integration requires OAuth 2.0 credentials. "
        "Set up a service account or OAuth consent screen in the "
        "Google Cloud Console, download credentials.json, and configure "
        "GOOGLE_DRIVE_CREDENTIALS_PATH and GOOGLE_DRIVE_FOLDER_ID env vars."
    )

    async def upload(self, key: str, data: bytes, **_kwargs: Any) -> dict[str, Any]:
        return {"ok": False, "note": self._NOTE}

    async def download(self, key: str) -> bytes:
        raise NotImplementedError(self._NOTE)

    async def list(self, prefix: str = "") -> list[str]:
        return []

    async def delete(self, key: str) -> bool:
        return False


# =====================================================================
# Factory
# =====================================================================


class StorageConnectorFactory:
    """Instantiate the right storage connector from a type string."""

    _registry: dict[str, type[BaseStorageConnector]] = {
        "s3": S3Connector,
        "local": LocalConnector,
        "google_drive": GoogleDriveStub,
    }

    @classmethod
    def get_connector(cls, connector_type: str, config: dict[str, Any]) -> BaseStorageConnector:
        klass = cls._registry.get(connector_type)
        if klass is None:
            raise ValueError(
                f"Unknown storage connector type: {connector_type!r}. "
                f"Available: {list(cls._registry)}"
            )
        return klass(config)
