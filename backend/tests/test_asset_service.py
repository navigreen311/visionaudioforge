"""Tests for the Asset Management service and API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _token_for(workspace_id) -> str:
    """A real signed token for *workspace_id* - see test_auth_enforcement.py."""
    import uuid as _uuid

    from app.core.security import create_access_token

    return create_access_token(
        {"sub": str(_uuid.uuid4()), "workspace_id": str(workspace_id)}
    )


def _auth_headers(workspace_id) -> dict:
    return {"Authorization": f"Bearer {_token_for(workspace_id)}"}


def _make_upload_file(
    filename: str = "test.png",
    content: bytes = b"fake-image-data",
    content_type: str = "image/png",
) -> UploadFile:
    """Create an UploadFile with an async-readable file object."""
    return UploadFile(filename=filename, file=BytesIO(content), headers={"content-type": content_type})


def _fake_asset_dict(**overrides: Any) -> dict[str, Any]:
    """Return a dict representing a persisted Asset row."""
    defaults: dict[str, Any] = {
        "id": uuid.uuid4(),
        "type": "image",
        "path": f"vaf-assets/{WORKSPACE_ID}/image/{uuid.uuid4()}_test.png",
        "filename": "test.png",
        "size_bytes": 15,
        "metadata_": {},
        "tags": ["test"],
        "workspace_id": WORKSPACE_ID,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    return defaults


def _fake_asset_obj(**overrides: Any) -> MagicMock:
    """Return a MagicMock that quacks like an Asset ORM instance."""
    d = _fake_asset_dict(**overrides)
    obj = MagicMock()
    for k, v in d.items():
        setattr(obj, k, v)
    return obj


def _mock_storage() -> AsyncMock:
    storage = AsyncMock()
    storage.upload_file = AsyncMock(return_value="vaf-assets/ws/image/uuid_test.png")
    storage.download_file = AsyncMock(return_value=b"file-bytes")
    storage.delete_file = AsyncMock(return_value=True)
    return storage


# ---------------------------------------------------------------------------
# Unit tests — AssetService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_asset_creates_record():
    """upload_asset should call storage.upload_file and add an Asset to the DB."""
    from app.services.assets.asset_service import AssetService

    db = AsyncMock()
    storage = _mock_storage()
    upload = _make_upload_file()

    fake_asset = _fake_asset_obj(
        filename="test.png",
        size_bytes=len(b"fake-image-data"),
        workspace_id=WORKSPACE_ID,
        type="image",
    )

    with patch("app.services.assets.asset_service.Asset", return_value=fake_asset):
        asset = await AssetService.upload_asset(
            db=db,
            storage=storage,
            file=upload,
            asset_type="image",
            workspace_id=WORKSPACE_ID,
        )

    storage.upload_file.assert_awaited_once()
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once()

    assert asset.filename == "test.png"
    assert asset.size_bytes == len(b"fake-image-data")
    assert asset.workspace_id == WORKSPACE_ID


@pytest.mark.asyncio
async def test_list_assets_filtered_by_type():
    """list_assets with asset_type filter should return matching assets."""
    from app.services.assets.asset_service import AssetService

    img_asset = _fake_asset_obj(type="image")

    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [img_asset]
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    assets, total = await AssetService.list_assets(
        db=db,
        workspace_id=WORKSPACE_ID,
        asset_type="image",
    )

    assert total == 1
    assert len(assets) == 1
    assert assets[0].type == "image"


@pytest.mark.asyncio
async def test_list_assets_filtered_by_tags():
    """list_assets with tags filter should return matching assets."""
    from app.services.assets.asset_service import AssetService

    tagged = _fake_asset_obj(tags=["nature", "landscape"])

    db = AsyncMock()
    count_result = MagicMock()
    count_result.scalar.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [tagged]
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    assets, total = await AssetService.list_assets(
        db=db,
        workspace_id=WORKSPACE_ID,
        tags=["nature"],
    )

    assert total == 1
    assert "nature" in assets[0].tags


@pytest.mark.asyncio
async def test_get_asset_returns_metadata():
    """get_asset should return a single Asset with its metadata."""
    from app.services.assets.asset_service import AssetService

    expected = _fake_asset_obj(metadata_={"source": "camera", "resolution": "1080p"})
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = expected
    db.execute = AsyncMock(return_value=result_mock)

    asset = await AssetService.get_asset(db, expected.id)

    assert asset.id == expected.id
    assert asset.metadata_["source"] == "camera"


@pytest.mark.asyncio
async def test_delete_asset_soft_deletes():
    """delete_asset should set metadata.deleted=True and call storage.delete_file."""
    from app.services.assets.asset_service import AssetService

    target = _fake_asset_obj(metadata_={})
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = target
    db.execute = AsyncMock(return_value=result_mock)
    storage = _mock_storage()

    result = await AssetService.delete_asset(db, storage, target.id)

    storage.delete_file.assert_awaited_once()
    assert result.metadata_.get("deleted") is True
    db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# API integration tests (via httpx / TestClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.auth_enforced
async def test_api_upload_endpoint(client):
    """POST /api/assets/upload should accept a file and return asset data.

    Marked ``auth_enforced`` and sent with a token for the workspace the body
    names: the route now derives the tenant from the session, because an upload
    with no owner is not an upload, and the browser has no business choosing one.
    """
    fake = _fake_asset_obj()

    with patch("app.api.routes.assets._get_storage", return_value=_mock_storage()):
        with patch(
            "app.api.routes.assets.AssetService.upload_asset",
            new_callable=AsyncMock,
            return_value=fake,
        ):
            response = await client.post(
                "/api/assets/upload",
                files={"file": ("test.png", b"fake-image-data", "image/png")},
                data={
                    "asset_type": "image",
                    "workspace_id": str(WORKSPACE_ID),
                },
                headers=_auth_headers(WORKSPACE_ID),
            )

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "test.png"
    assert body["type"] == "image"


@pytest.mark.asyncio
@pytest.mark.auth_enforced
async def test_api_list_endpoint(client):
    """GET /api/assets should return a paginated response."""
    fake = _fake_asset_obj()

    with patch(
        "app.api.routes.assets.AssetService.list_assets",
        new_callable=AsyncMock,
        return_value=([fake], 1),
    ):
        response = await client.get(
            "/api/assets",
            params={"workspace_id": str(WORKSPACE_ID)},
            headers=_auth_headers(WORKSPACE_ID),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["filename"] == "test.png"
