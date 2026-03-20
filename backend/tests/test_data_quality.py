"""Tests for data quality, auto-labeling, active learning, and synthetic data."""

from __future__ import annotations

import datetime as dt
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# Lightweight fakes (same pattern as test_dataset_manager.py)
# ---------------------------------------------------------------------------

_FAKE_WORKSPACE = uuid.uuid4()


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
        self.tags = kw.get("tags", [])


class FakeDataset:
    """Minimal stand-in for the Dataset model."""

    def __init__(self, **kw):
        self.id = kw.get("id", uuid.uuid4())
        self.name = kw.get("name", "test-ds")
        self.description = kw.get("description", "")
        self.format = kw.get("format", "image")
        self.item_count = kw.get("item_count", 0)
        self.size_bytes = kw.get("size_bytes", 0)
        self.metadata_ = kw.get("metadata_", {"modality": "image", "version": 1})
        self.workspace_id = kw.get("workspace_id", _FAKE_WORKSPACE)
        self.created_at = kw.get("created_at", dt.datetime.now(dt.timezone.utc))
        self.updated_at = kw.get("updated_at", dt.datetime.now(dt.timezone.utc))


class FakeDB:
    """Stub for AsyncSession."""

    def __init__(self):
        self._store: dict[uuid.UUID, FakeAsset | FakeDataset] = {}
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

    async def download_file(self, bucket, key):
        return b""


# ---------------------------------------------------------------------------
# Quality control tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_class_imbalance_detection():
    """Imbalanced dataset (ratio > 5) should be flagged."""
    from app.services.data.quality_control import DatasetQualityService

    ds_id = uuid.uuid4()
    db = FakeDB()

    # 50 "cat" + 5 "dog" → ratio = 10 → imbalanced
    db._assets = [
        FakeAsset(metadata_={"dataset_id": str(ds_id), "label": "cat"})
        for _ in range(50)
    ] + [
        FakeAsset(metadata_={"dataset_id": str(ds_id), "label": "dog"})
        for _ in range(5)
    ]

    result = await DatasetQualityService.check_class_imbalance(db, ds_id)

    assert result["is_imbalanced"] is True
    assert result["class_counts"]["cat"] == 50
    assert result["class_counts"]["dog"] == 5
    assert result["imbalance_ratio"] == 10.0
    assert result["max_class"] == "cat"
    assert result["min_class"] == "dog"
    assert "oversample" in result["recommendation"].lower()


@pytest.mark.asyncio
async def test_health_report_complete():
    """Health report should contain all expected keys."""
    from app.services.data.quality_control import DatasetQualityService

    ds_id = uuid.uuid4()
    db = FakeDB()
    db._assets = [
        FakeAsset(
            size_bytes=100,
            media_type="image",
            metadata_={"dataset_id": str(ds_id), "label": "cat"},
        )
        for _ in range(20)
    ] + [
        FakeAsset(
            size_bytes=200,
            media_type="image",
            metadata_={"dataset_id": str(ds_id), "label": "dog"},
        )
        for _ in range(20)
    ]

    report = await DatasetQualityService.generate_health_report(db, ds_id)

    assert report["total_samples"] == 40
    assert "cat" in report["class_distribution"]
    assert "dog" in report["class_distribution"]
    assert isinstance(report["is_imbalanced"], bool)
    assert isinstance(report["duplicate_count"], int)
    assert isinstance(report["corrupt_count"], int)
    assert report["avg_size_bytes"] > 0
    assert isinstance(report["modality_mix"], dict)
    assert 0 <= report["annotation_coverage"] <= 1.0
    assert 0 <= report["quality_score"] <= 100
    assert isinstance(report["issues"], list)
    assert isinstance(report["recommendations"], list)


@pytest.mark.asyncio
async def test_near_duplicate_finds_identical():
    """Two assets with identical filename+size should be flagged by dedup."""
    from app.services.data.quality_control import DatasetQualityService

    ds_id = uuid.uuid4()
    db = FakeDB()

    db._assets = [
        FakeAsset(filename="same.png", size_bytes=1024,
                  metadata_={"dataset_id": str(ds_id)}),
        FakeAsset(filename="same.png", size_bytes=1024,
                  metadata_={"dataset_id": str(ds_id)}),
        FakeAsset(filename="other.png", size_bytes=2048,
                  metadata_={"dataset_id": str(ds_id)}),
    ]

    result = await DatasetQualityService.deduplicate(db, ds_id, keep="first")

    assert result["removed"] == 1
    assert result["kept"] == 2


@pytest.mark.asyncio
async def test_corrupt_detection():
    """Corrupt detection should handle missing files gracefully."""
    from app.services.data.quality_control import DatasetQualityService

    ds_id = uuid.uuid4()
    db = FakeDB()
    db._assets = [
        FakeAsset(
            storage_path="/nonexistent/path.png",
            media_type="image",
            metadata_={"dataset_id": str(ds_id)},
        ),
    ]

    storage = FakeStorage()
    result = await DatasetQualityService.detect_corrupt_samples(db, storage, ds_id)

    # Should flag the asset since file can't be loaded
    assert len(result) >= 1
    assert "asset_id" in result[0]
    assert "error" in result[0]


# ---------------------------------------------------------------------------
# Active learning tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uncertainty_sampling_returns_k():
    """Uncertainty sampling should return at most k asset IDs."""
    from app.services.data.active_learning import ActiveLearningService

    ds_id = uuid.uuid4()
    db = FakeDB()
    db._assets = [
        FakeAsset(metadata_={"dataset_id": str(ds_id)})
        for _ in range(100)
    ]

    result = await ActiveLearningService.uncertainty_sampling(
        db, ds_id, model_name="yolov8n", k=10
    )

    assert len(result) == 10
    # Each item should be a string (UUID)
    assert all(isinstance(x, str) for x in result)


@pytest.mark.asyncio
async def test_diversity_sampling_returns_k():
    """Diversity sampling should return at most k asset IDs."""
    from app.services.data.active_learning import ActiveLearningService

    ds_id = uuid.uuid4()
    db = FakeDB()
    db._assets = [
        FakeAsset(
            filename=f"img_{i}.png",
            size_bytes=1000 + i * 100,
            metadata_={"dataset_id": str(ds_id)},
        )
        for i in range(100)
    ]

    result = await ActiveLearningService.diversity_sampling(db, ds_id, k=10)

    assert len(result) == 10
    assert all(isinstance(x, str) for x in result)
    # All returned IDs should be unique
    assert len(set(result)) == 10


# ---------------------------------------------------------------------------
# Synthetic data tests
# ---------------------------------------------------------------------------


def test_synthetic_image_generation():
    """Generate synthetic images with the shapes pattern."""
    from app.services.data.synthetic import SyntheticDataGenerator

    images = SyntheticDataGenerator.generate_synthetic_images(
        num=5, width=64, height=64, pattern="shapes"
    )

    assert len(images) == 5
    for img in images:
        assert isinstance(img, np.ndarray)
        assert img.shape == (64, 64, 3)
        assert img.dtype == np.uint8


def test_synthetic_audio_generation():
    """Generate synthetic audio waveforms."""
    from app.services.data.synthetic import SyntheticDataGenerator

    waveforms = SyntheticDataGenerator.generate_synthetic_audio(
        num=3, duration=0.5, sr=16000, pattern="tones"
    )

    assert len(waveforms) == 3
    for wav in waveforms:
        assert isinstance(wav, np.ndarray)
        assert wav.dtype == np.float32
        expected_len = int(16000 * 0.5)
        assert len(wav) == expected_len


# ---------------------------------------------------------------------------
# Auto-labeling tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_label_creates_annotations():
    """Auto-labeling should skip already-labeled assets and mark new ones."""
    from app.services.data.auto_labeling import AutoLabelingService

    ds_id = uuid.uuid4()
    db = FakeDB()

    # 2 unlabeled, 1 already labeled
    db._assets = [
        FakeAsset(metadata_={"dataset_id": str(ds_id)}),
        FakeAsset(metadata_={"dataset_id": str(ds_id)}),
        FakeAsset(metadata_={"dataset_id": str(ds_id), "label": "existing"}),
    ]

    # Mock YOLO since ultralytics may not be installed
    fake_yolo_cls = MagicMock()
    with patch.dict("sys.modules", {"ultralytics": MagicMock(YOLO=fake_yolo_cls)}):
        # Since we can't actually load images, the unlabeled ones will be skipped
        # (no real file on disk), and the labeled one will also be skipped
        result = await AutoLabelingService.auto_label_images(db, ds_id)

    assert "labeled" in result
    assert "skipped" in result
    assert "below_threshold" in result
    # The already-labeled asset should be counted as skipped
    assert result["skipped"] >= 1


@pytest.mark.asyncio
async def test_review_queue():
    """Review queue should return low-confidence auto-labeled assets."""
    from app.services.data.auto_labeling import AutoLabelingService

    ds_id = uuid.uuid4()
    db = FakeDB()
    db._assets = [
        FakeAsset(metadata_={
            "dataset_id": str(ds_id),
            "annotations": [{"label": "cat", "confidence": 0.5, "is_verified": False}],
        }),
        FakeAsset(metadata_={
            "dataset_id": str(ds_id),
            "annotations": [{"label": "dog", "confidence": 0.9, "is_verified": False}],
        }),
        FakeAsset(metadata_={
            "dataset_id": str(ds_id),
            "annotations": [{"label": "bird", "confidence": 0.4, "is_verified": False}],
        }),
    ]

    result = await AutoLabelingService.review_queue(
        db, ds_id, confidence_range=(0.3, 0.7)
    )

    # Should include the 0.5 and 0.4 confidence items, not the 0.9 one
    assert len(result) == 2
    confidences = [r["confidence"] for r in result]
    assert 0.9 not in confidences
    assert 0.5 in confidences
    assert 0.4 in confidences


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_api_quality_report():
    """GET /api/datasets/{id}/quality should return a health report."""
    from app.main import app

    ds_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "app.api.routes.datasets.DatasetQualityService"
        ) as MockQuality:
            MockQuality.generate_health_report = AsyncMock(
                return_value={
                    "total_samples": 100,
                    "class_distribution": {"cat": 60, "dog": 40},
                    "is_imbalanced": False,
                    "duplicate_count": 0,
                    "corrupt_count": 0,
                    "avg_size_bytes": 2048.0,
                    "modality_mix": {"image": 100},
                    "annotation_coverage": 0.85,
                    "quality_score": 90.0,
                    "issues": [],
                    "recommendations": [],
                }
            )
            resp = await client.get(f"/api/datasets/{ds_id}/quality")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_samples"] == 100
    assert body["quality_score"] == 90.0
    assert "class_distribution" in body


@pytest.mark.asyncio
async def test_api_auto_label():
    """POST /api/datasets/{id}/auto-label should invoke auto-labeling."""
    from app.main import app

    ds_id = uuid.uuid4()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch(
            "app.api.routes.datasets.AutoLabelingService"
        ) as MockAL:
            MockAL.auto_label_images = AsyncMock(
                return_value={"labeled": 10, "skipped": 5, "below_threshold": 3}
            )
            resp = await client.post(
                f"/api/datasets/{ds_id}/auto-label",
                json={"model_name": "yolov8n", "confidence_threshold": 0.7},
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["labeled"] == 10
    assert body["skipped"] == 5
    assert body["below_threshold"] == 3
