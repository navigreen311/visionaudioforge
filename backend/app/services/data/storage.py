"""MinIO object storage service for file upload/download/management."""

from __future__ import annotations

import io
import logging
from typing import Any

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


class MinIOStorageService:
    """Thin async-style wrapper around the minio-py SDK.

    Note: The minio Python SDK is synchronous under the hood.  We keep the
    ``async`` signatures so callers (FastAPI route handlers) can ``await``
    them uniformly; the actual I/O is delegated to the SDK which uses
    ``urllib3``.  For truly non-blocking behaviour in production you would
    run these calls in a thread-pool executor — that optimisation is left
    for a follow-up.
    """

    def __init__(self) -> None:
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,  # dev — no TLS
        )

    # ------------------------------------------------------------------
    # Bucket helpers
    # ------------------------------------------------------------------

    async def ensure_bucket(self, bucket: str) -> None:
        """Create *bucket* if it does not already exist."""
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info("Created bucket: %s", bucket)
        except S3Error as exc:
            logger.error("MinIO bucket check/create failed: %s", exc)
            raise

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def upload_file(
        self,
        bucket: str,
        key: str,
        file_data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload *file_data* to *bucket/key* and return the object path."""
        await self.ensure_bucket(bucket)
        try:
            self.client.put_object(
                bucket_name=bucket,
                object_name=key,
                data=io.BytesIO(file_data),
                length=len(file_data),
                content_type=content_type,
            )
            url = f"{bucket}/{key}"
            logger.info("Uploaded %s (%d bytes)", url, len(file_data))
            return url
        except S3Error as exc:
            logger.error("Upload failed for %s/%s: %s", bucket, key, exc)
            raise

    async def download_file(self, bucket: str, key: str) -> bytes:
        """Download and return the raw bytes for *bucket/key*."""
        try:
            response = self.client.get_object(bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as exc:
            logger.error("Download failed for %s/%s: %s", bucket, key, exc)
            raise

    async def list_files(
        self, bucket: str, prefix: str = ""
    ) -> list[dict[str, Any]]:
        """Return a list of object metadata dicts under *prefix*."""
        try:
            objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
            return [
                {
                    "key": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
                }
                for obj in objects
            ]
        except S3Error as exc:
            logger.error("List failed for %s/%s: %s", bucket, prefix, exc)
            raise

    async def delete_file(self, bucket: str, key: str) -> bool:
        """Delete *bucket/key*.  Returns ``True`` on success."""
        try:
            self.client.remove_object(bucket, key)
            logger.info("Deleted %s/%s", bucket, key)
            return True
        except S3Error as exc:
            logger.error("Delete failed for %s/%s: %s", bucket, key, exc)
            return False
