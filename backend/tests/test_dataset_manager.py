"""Tests for the Dataset Manager (M7)."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Lightweight in-memory fakes for DB + Storage so we can test service logic
# without Postgres / MinIO.
# ---------------------------------------------------------------------------

_FAKE_WORKSPACE = uuid.uuid4()


def _token_for(workspace_id: uuid.UUID) -> str:
    """A real signed token for *workspace_id* — see test_auth_enforcement.py."""
    from app.core.security import create_access_token

    return create_access_token(
        {"sub": str(uuid.uuid4()), "workspace_id": str(workspace_id)}
    )


class FakeAsset:
    """Minimal stand-in for the Asset model."""

    def __init__(self, **kw):
        self.id = kw.get("id", uuid.uuid4())
        self.filename = kw.get("filename", "file.png")
        self.media_type = kw.get("media_type", "image")
        self.mime_type = kw.get("mime_type", "image/png")
        self.size_bytes = kw.get("size_bytes", 1024)
        self.storage_path = kw.get("storage_path", "vaf-datasets/x/file.png")
        self.metadata_ = kw.get("metadata_", {})
        self.workspace_id = kw.get("workspace_id", _FAKE_WORKSPACE)


class FakeDataset:
    """Minimal stand-in for the Dataset model.

    Mirrors the columns `datasets` actually has. It used to carry
    format/item_count/size_bytes/metadata_, none of which exist on the table,
    so it agreed with a service that could not talk to the database.
    """

    def __init__(self, **kw):
        self.id = kw.get("id", uuid.uuid4())
        self.name = kw.get("name", "test-ds")
        self.modality = kw.get("modality", "image")
        self.version = kw.get("version", "1.0")
        self.stats = kw.get("stats", {"description": "", "total_size_bytes": 0})
        self.sample_count = kw.get("sample_count", 0)
        self.workspace_id = kw.get("workspace_id", _FAKE_WORKSPACE)
        self.created_at = kw.get("created_at", None)
        self.updated_at = kw.get("updated_at", None)


class FakeDB:
    """Very small stub for AsyncSession used by DatasetService."""

    def __init__(self):
        self._store: dict[uuid.UUID, FakeDataset | FakeAsset] = {}
        self._assets: list[FakeAsset] = []

    async def commit(self):
        pass

    async def refresh(self, obj):
        if obj.id is None:
            obj.id = uuid.uuid4()

    async def get(self, model, pk):
        return self._store.get(pk)

    def add(self, obj):
        if hasattr(obj, "item_count"):
            self._store[obj.id] = obj
        else:
            self._assets.append(obj)
            self._store[obj.id] = obj

    async def execute(self, stmt):
        """Crude matcher — returns canned results."""
        return FakeResult(self._assets)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return len(self._rows)


class FakeStorage:
    async def upload_file(self, bucket, key, file_data, content_type="application/octet-stream"):
        return f"{bucket}/{key}"


class FakeUploadFile:
    def __init__(self, filename, data=b"x", content_type="image/png"):
        self.filename = filename
        self.content_type = content_type
        self._data = data

    async def read(self):
        return self._data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_dataset():
    db = FakeDB()
    from app.services.data.dataset_manager import DatasetService

    # Patch the model import so commit/refresh go through FakeDB
    ds_id = uuid.uuid4()

    with patch("app.services.data.dataset_manager.Dataset") as MockDS:
        fake_ds = FakeDataset(id=ds_id, name="cats", modality="image")
        MockDS.return_value = fake_ds
        result = await DatasetService.create_dataset(db, "cats", "image", _FAKE_WORKSPACE)

    assert result.name == "cats"
    assert result.modality == "image"


@pytest.mark.asyncio
async def test_upload_samples_increments_count():
    ds_id = uuid.uuid4()
    fake_ds = FakeDataset(id=ds_id, sample_count=0)
    db = FakeDB()
    db._store[ds_id] = fake_ds

    files = [FakeUploadFile("a.png"), FakeUploadFile("b.png")]
    storage = FakeStorage()

    from app.services.data.dataset_manager import DatasetService

    result = await DatasetService.upload_samples(db, storage, ds_id, files, None)

    assert result["uploaded"] == 2
    assert result["failed"] == 0
    assert fake_ds.sample_count == 2


@pytest.mark.asyncio
async def test_list_datasets_paginated():
    """list_datasets should return a (list, total) tuple."""
    from app.services.data.dataset_manager import DatasetService

    db = FakeDB()
    # We can't easily test the SQL query with fakes, but we can verify
    # the function signature and return types.
    result = await DatasetService.list_datasets(db, _FAKE_WORKSPACE, skip=0, limit=10)
    assert isinstance(result, tuple)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_compute_stats():
    ds_id = uuid.uuid4()
    fake_ds = FakeDataset(id=ds_id, sample_count=0, stats={"modality": "image"})
    db = FakeDB()
    db._store[ds_id] = fake_ds
    db._assets = [
        FakeAsset(size_bytes=100, media_type="image", metadata_={"dataset_id": str(ds_id), "label": "cat"}),
        FakeAsset(size_bytes=200, media_type="image", metadata_={"dataset_id": str(ds_id), "label": "dog"}),
        FakeAsset(size_bytes=150, media_type="image", metadata_={"dataset_id": str(ds_id), "label": "cat"}),
    ]

    from app.services.data.dataset_manager import DatasetService

    stats = await DatasetService.compute_stats(db, ds_id)

    assert stats["total_samples"] == 3
    assert stats["total_size_bytes"] == 450
    assert stats["label_distribution"]["cat"] == 2
    assert stats["label_distribution"]["dog"] == 1


@pytest.mark.asyncio
async def test_split_ratios_sum_correctly():
    ds_id = uuid.uuid4()
    db = FakeDB()
    fake_ds = FakeDataset(id=ds_id)
    db._store[ds_id] = fake_ds
    db._assets = [
        FakeAsset(metadata_={"dataset_id": str(ds_id), "label": "a"})
        for _ in range(100)
    ]

    from app.services.data.dataset_manager import DatasetService

    result = await DatasetService.split_dataset(
        db, ds_id, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, stratified=False
    )
    total = result["train"] + result["val"] + result["test"]
    assert total == 100
    assert result["train"] == 70
    assert result["val"] == 15


@pytest.mark.asyncio
async def test_split_stratified_preserves_distribution():
    ds_id = uuid.uuid4()
    db = FakeDB()
    fake_ds = FakeDataset(id=ds_id)
    db._store[ds_id] = fake_ds
    # 80 "cat" + 20 "dog" = 100 assets
    db._assets = [
        FakeAsset(metadata_={"dataset_id": str(ds_id), "label": "cat"})
        for _ in range(80)
    ] + [
        FakeAsset(metadata_={"dataset_id": str(ds_id), "label": "dog"})
        for _ in range(20)
    ]

    from app.services.data.dataset_manager import DatasetService

    result = await DatasetService.split_dataset(
        db, ds_id, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15, stratified=True
    )
    total = result["train"] + result["val"] + result["test"]
    assert total == 100

    # Count splits per label to verify stratification
    label_splits: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for a in db._assets:
        label = a.metadata_.get("label")
        split = a.metadata_.get("split")
        label_splits[label][split] += 1

    # Each label group should have some representation in train
    assert label_splits["cat"]["train"] > 0
    assert label_splits["dog"]["train"] > 0


@pytest.mark.asyncio
async def test_export_returns_json():
    ds_id = uuid.uuid4()
    fake_ds = FakeDataset(id=ds_id, name="export-test")
    db = FakeDB()
    db._store[ds_id] = fake_ds
    db._assets = [
        FakeAsset(metadata_={"dataset_id": str(ds_id), "label": "x"}),
    ]
    storage = FakeStorage()

    from app.services.data.dataset_manager import DatasetService

    data = await DatasetService.export_dataset(db, storage, ds_id, "json")
    parsed = json.loads(data)
    assert parsed["dataset"]["name"] == "export-test"
    assert len(parsed["samples"]) == 1


@pytest.mark.asyncio
@pytest.mark.auth_enforced
async def test_api_create_dataset():
    """POST /api/datasets should return 201.

    Runs with the auth boundary on, and sends a token minted for the same
    workspace the body names. The route now derives the tenant from the session
    (a dataset with no owner is not a dataset), and TenantGuardMiddleware refuses
    a body that names a different one — so an anonymous POST, which is what this
    test used to send, is correctly rejected.
    """
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.api.routes.datasets.DatasetService") as MockSvc:
            import datetime as dt

            fake_ds = FakeDataset(
                name="api-test",
                modality="image",
                created_at=dt.datetime.now(dt.timezone.utc),
                updated_at=dt.datetime.now(dt.timezone.utc),
            )
            MockSvc.create_dataset = AsyncMock(return_value=fake_ds)

            resp = await client.post(
                "/api/datasets",
                json={
                    "name": "api-test",
                    "modality": "image",
                    "workspace_id": str(_FAKE_WORKSPACE),
                },
                headers={"Authorization": f"Bearer {_token_for(_FAKE_WORKSPACE)}"},
            )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "api-test"


@pytest.mark.asyncio
async def test_api_upload_endpoint():
    """POST /api/datasets/{id}/upload should accept multipart files."""
    from app.main import app

    ds_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.api.routes.datasets.DatasetService") as MockSvc:
            MockSvc.upload_samples = AsyncMock(
                return_value={"uploaded": 1, "failed": 0, "errors": []}
            )
            resp = await client.post(
                f"/api/datasets/{ds_id}/upload",
                files=[("files", ("test.png", b"fake-image-data", "image/png"))],
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["uploaded"] == 1
