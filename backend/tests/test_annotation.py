"""Tests for the Annotation service and API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ASSET_ID = uuid.uuid4()
DATASET_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


def _fake_annotation(**overrides: Any) -> MagicMock:
    """Return a MagicMock that quacks like an Annotation ORM instance."""
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "asset_id": ASSET_ID,
        "dataset_id": DATASET_ID,
        "user_id": USER_ID,
        "annotation_type": "bbox",
        "data": {"x": 10, "y": 20, "width": 100, "height": 50, "label": "car"},
        "is_verified": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _fake_asset(asset_id: uuid.UUID | None = None, **overrides: Any) -> MagicMock:
    """Return a MagicMock that quacks like an Asset ORM instance."""
    defaults: dict[str, Any] = {
        "id": asset_id or ASSET_ID,
        "filename": "test.png",
        "path": "vaf-assets/test.png",
        "type": "image",
        "metadata_": {"width": 640, "height": 480},
    }
    defaults.update(overrides)
    obj = MagicMock()
    for k, v in defaults.items():
        setattr(obj, k, v)
    return obj


def _mock_db_session() -> AsyncMock:
    """Create a mock async DB session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Unit tests: AnnotationService
# ---------------------------------------------------------------------------


class TestAnnotationServiceCreate:
    """Tests for AnnotationService.create_annotation."""

    @pytest.mark.anyio
    async def test_create_bbox_annotation(self):
        """Creating a bbox annotation should persist with correct type and data."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()

        async def _refresh(obj: Any) -> None:
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        db.refresh = AsyncMock(side_effect=_refresh)

        ann = await AnnotationService.create_annotation(
            db=db,
            asset_id=ASSET_ID,
            annotation_type="bbox",
            data={"x": 10, "y": 20, "width": 100, "height": 50, "label": "car"},
            user_id=USER_ID,
            dataset_id=DATASET_ID,
        )

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        assert ann.annotation_type == "bbox"
        assert ann.data["label"] == "car"

    @pytest.mark.anyio
    async def test_create_polygon_annotation(self):
        """Creating a polygon annotation should store point data."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()

        async def _refresh(obj: Any) -> None:
            obj.id = uuid.uuid4()
            obj.created_at = datetime.now(timezone.utc)
            obj.updated_at = datetime.now(timezone.utc)

        db.refresh = AsyncMock(side_effect=_refresh)

        points = [[10, 20], [30, 40], [50, 20]]
        ann = await AnnotationService.create_annotation(
            db=db,
            asset_id=ASSET_ID,
            annotation_type="polygon",
            data={"points": points, "label": "building"},
            user_id=USER_ID,
        )

        assert ann.annotation_type == "polygon"
        assert ann.data["points"] == points

    @pytest.mark.anyio
    async def test_create_invalid_type_raises(self):
        """Creating an annotation with invalid type should raise ValueError."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()

        with pytest.raises(ValueError, match="Invalid annotation_type"):
            await AnnotationService.create_annotation(
                db=db,
                asset_id=ASSET_ID,
                annotation_type="invalid_type",
                data={},
                user_id=USER_ID,
            )


class TestAnnotationServiceRead:
    """Tests for get/list annotations."""

    @pytest.mark.anyio
    async def test_get_annotations_for_asset(self):
        """get_annotations should return all annotations for a given asset."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()
        fake_anns = [_fake_annotation(), _fake_annotation(annotation_type="polygon")]
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = fake_anns
        db.execute = AsyncMock(return_value=result_mock)

        result = await AnnotationService.get_annotations(db, ASSET_ID)
        assert len(result) == 2


class TestAnnotationServiceUpdate:
    """Tests for update_annotation."""

    @pytest.mark.anyio
    async def test_update_annotation(self):
        """Updating an annotation should change its data."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()
        existing = _fake_annotation()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        db.execute = AsyncMock(return_value=result_mock)

        new_data = {"x": 50, "y": 60, "width": 200, "height": 100, "label": "truck"}
        ann = await AnnotationService.update_annotation(db, existing.id, new_data)
        assert ann.data == new_data
        db.commit.assert_awaited_once()


class TestAnnotationServiceDelete:
    """Tests for delete_annotation."""

    @pytest.mark.anyio
    async def test_delete_annotation(self):
        """Deleting an existing annotation should return True."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()
        existing = _fake_annotation()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        db.execute = AsyncMock(return_value=result_mock)

        deleted = await AnnotationService.delete_annotation(db, existing.id)
        assert deleted is True
        db.delete.assert_awaited_once()

    @pytest.mark.anyio
    async def test_delete_nonexistent_returns_false(self):
        """Deleting a non-existent annotation should return False."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        deleted = await AnnotationService.delete_annotation(db, uuid.uuid4())
        assert deleted is False


class TestAnnotationServiceExport:
    """Tests for export_annotations."""

    @pytest.mark.anyio
    async def test_export_coco_format(self):
        """COCO export should produce images, annotations, categories."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()
        anns = [
            _fake_annotation(annotation_type="bbox", data={"x": 10, "y": 20, "width": 100, "height": 50, "label": "car"}),
            _fake_annotation(annotation_type="bbox", data={"x": 50, "y": 60, "width": 80, "height": 40, "label": "person"}),
        ]
        asset = _fake_asset()

        # First execute call: get annotations
        anns_result = MagicMock()
        anns_result.scalars.return_value.all.return_value = anns

        # Second execute call: get assets
        assets_result = MagicMock()
        assets_result.scalars.return_value.all.return_value = [asset]

        db.execute = AsyncMock(side_effect=[anns_result, assets_result])

        result = await AnnotationService.export_annotations(db, DATASET_ID, format="coco")

        assert "images" in result
        assert "annotations" in result
        assert "categories" in result
        assert len(result["annotations"]) == 2
        assert len(result["categories"]) == 2  # car, person

    @pytest.mark.anyio
    async def test_export_yolo_format(self):
        """YOLO export should produce class list and text files."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()
        anns = [
            _fake_annotation(annotation_type="bbox", data={"x": 10, "y": 20, "width": 100, "height": 50, "label": "car"}),
        ]
        asset = _fake_asset()

        anns_result = MagicMock()
        anns_result.scalars.return_value.all.return_value = anns
        assets_result = MagicMock()
        assets_result.scalars.return_value.all.return_value = [asset]
        db.execute = AsyncMock(side_effect=[anns_result, assets_result])

        result = await AnnotationService.export_annotations(db, DATASET_ID, format="yolo")

        assert result["format"] == "yolo"
        assert "car" in result["classes"]
        assert "test.txt" in result["files"]
        line = result["files"]["test.txt"]
        parts = line.strip().split()
        assert len(parts) == 5  # class_id cx cy w h


class TestAnnotationServiceImport:
    """Tests for import_annotations."""

    @pytest.mark.anyio
    async def test_import_annotations(self):
        """Importing COCO annotations should create annotation records."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()
        asset = _fake_asset()

        # Mock db.execute for the asset lookup
        asset_result = MagicMock()
        asset_result.scalar_one_or_none.return_value = asset
        db.execute = AsyncMock(return_value=asset_result)

        coco_data = {
            "images": [{"id": 1, "file_name": "test.png", "width": 640, "height": 480}],
            "annotations": [
                {"id": 1, "image_id": 1, "category_id": 1, "bbox": [10, 20, 100, 50]},
                {"id": 2, "image_id": 1, "category_id": 2, "bbox": [50, 60, 80, 40]},
            ],
            "categories": [
                {"id": 1, "name": "car"},
                {"id": 2, "name": "person"},
            ],
        }

        result = await AnnotationService.import_annotations(db, DATASET_ID, coco_data, format="coco")
        assert result["imported"] == 2
        assert db.add.call_count == 2


class TestAnnotationServiceStats:
    """Tests for annotation_stats."""

    @pytest.mark.anyio
    async def test_annotation_stats(self):
        """Stats should return total, by_type, by_label, and annotated_pct."""
        from app.services.data.annotation import AnnotationService

        db = _mock_db_session()
        anns = [
            _fake_annotation(annotation_type="bbox", data={"label": "car"}),
            _fake_annotation(annotation_type="bbox", data={"label": "car"}),
            _fake_annotation(annotation_type="polygon", data={"label": "building"}),
        ]

        # First execute: annotations
        anns_result = MagicMock()
        anns_result.scalars.return_value.all.return_value = anns

        # Second execute: total asset count
        count_result = MagicMock()
        count_result.scalar.return_value = 10

        db.execute = AsyncMock(side_effect=[anns_result, count_result])

        stats = await AnnotationService.annotation_stats(db, DATASET_ID)

        assert stats["total"] == 3
        assert stats["by_type"]["bbox"] == 2
        assert stats["by_type"]["polygon"] == 1
        assert stats["by_label"]["car"] == 2
        assert stats["by_label"]["building"] == 1
        assert stats["annotated_pct"] == 10.0  # 1 unique asset / 10 total * 100


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


class TestAnnotationAPI:
    """Tests for annotation API routes using test client."""

    @pytest.mark.anyio
    async def test_api_create(self, test_app):
        """POST /api/annotations should create an annotation."""
        with patch("app.api.routes.annotations.AnnotationService.create_annotation") as mock_create:
            fake = _fake_annotation()
            mock_create.return_value = fake

            resp = await test_app.post("/api/annotations", json={
                "asset_id": str(ASSET_ID),
                "annotation_type": "bbox",
                "data": {"x": 10, "y": 20, "width": 100, "height": 50, "label": "car"},
                "user_id": str(USER_ID),
            })

            assert resp.status_code == 200
            body = resp.json()
            assert body["annotation_type"] == "bbox"

    @pytest.mark.anyio
    async def test_api_export(self, test_app):
        """POST /api/datasets/{id}/annotations/export should return annotations."""
        with patch("app.api.routes.annotations.AnnotationService.export_annotations") as mock_export:
            mock_export.return_value = {
                "images": [{"id": 1, "file_name": "test.png"}],
                "annotations": [{"id": 1, "image_id": 1}],
                "categories": [{"id": 1, "name": "car"}],
            }

            resp = await test_app.post(
                f"/api/datasets/{DATASET_ID}/annotations/export?format=coco"
            )

            assert resp.status_code == 200
            body = resp.json()
            assert "images" in body
            assert "annotations" in body
