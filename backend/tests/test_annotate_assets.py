"""The annotation studio's thumbnail strip, against a real Postgres.

This endpoint returned 500 in the deployed stack while every unit test passed,
because the failure was a *SQL* one that only a real database raises:

    asyncpg.UndefinedFunctionError: could not identify an equality operator
    for type json

It selected assets with an outer join to annotations, which can match one asset
once per annotation, so it needed DISTINCT to deduplicate. DISTINCT compares
whole rows; `assets.metadata` is a `json` column; and PostgreSQL defines equality
only for `jsonb`. The studio showed "No assets loaded" for a dataset that had
assets, and only the browser suite noticed.

These tests exercise the endpoint against Postgres so the same class of defect -
a query that is valid Python and invalid SQL - fails here rather than in a
browser.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token
from app.core.tenancy import unscoped
from app.database import async_session_factory
from app.models.annotation import Annotation
from app.models.asset import Asset
from app.models.dataset import Dataset
from app.models.user import User
from app.models.workspace import Workspace

pytestmark = [pytest.mark.anyio, pytest.mark.auth_enforced]


def _auth(workspace_id: uuid.UUID) -> dict[str, str]:
    token = create_access_token(
        {"sub": str(uuid.uuid4()), "workspace_id": str(workspace_id)}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def seeded():
    """A workspace with one dataset holding two assets.

    One asset is linked through an `annotations` row, the other through the
    `metadata->>'dataset_id'` path, because the endpoint accepts both and the
    join/DISTINCT bug only appeared on the first.
    """
    stamp = uuid.uuid4().hex[:8]
    workspace_id = uuid.uuid4()
    dataset_id = uuid.uuid4()

    async with async_session_factory() as db:
        with unscoped():  # setup, not the query under test
            db.add(
                Workspace(
                    id=workspace_id, name=f"annot-{stamp}", slug=f"annot-{stamp}"
                )
            )
            await db.flush()

            user = User(
                id=uuid.uuid4(),
                email=f"annot-{stamp}@example.com",
                hashed_password="x",
                workspace_id=workspace_id,
            )
            db.add(user)
            db.add(
                Dataset(
                    id=dataset_id,
                    name=f"dataset-{stamp}",
                    modality="image",
                    workspace_id=workspace_id,
                )
            )
            await db.flush()

            via_annotation = Asset(
                type="image",
                path=f"{workspace_id}/image/via-annotation.png",
                filename="via-annotation.png",
                size_bytes=10,
                workspace_id=workspace_id,
            )
            via_metadata = Asset(
                type="image",
                path=f"{workspace_id}/image/via-metadata.png",
                filename="via-metadata.png",
                size_bytes=10,
                metadata_={"dataset_id": str(dataset_id)},
                workspace_id=workspace_id,
            )
            db.add_all([via_annotation, via_metadata])
            await db.flush()

            # Two annotations on the same asset: the shape that made DISTINCT
            # necessary in the first place, and so the shape that broke it.
            for _ in range(2):
                db.add(
                    Annotation(
                        asset_id=via_annotation.id,
                        dataset_id=dataset_id,
                        user_id=user.id,
                        annotation_type="bbox",
                        data={"x": 1},
                    )
                )
            await db.commit()

    return {"workspace_id": workspace_id, "dataset_id": dataset_id}


@pytest.fixture
async def client():
    transport = ASGITransport(app=__import__("app.main", fromlist=["app"]).app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_a_dataset_with_assets_does_not_report_none(client, seeded):
    """The regression: this answered 500, which the console rendered as empty."""
    response = await client.get(
        "/api/annotate/assets",
        params={
            "dataset_id": str(seeded["dataset_id"]),
            "workspace_id": str(seeded["workspace_id"]),
        },
        headers=_auth(seeded["workspace_id"]),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    filenames = [item["filename"] for item in body["items"]]
    assert "via-annotation.png" in filenames
    assert "via-metadata.png" in filenames


async def test_an_asset_appears_once_however_many_annotations_it_has(client, seeded):
    """The reason DISTINCT was there. EXISTS gives this by construction."""
    response = await client.get(
        "/api/annotate/assets",
        params={"dataset_id": str(seeded["dataset_id"])},
        headers=_auth(seeded["workspace_id"]),
    )

    assert response.status_code == 200, response.text
    filenames = [item["filename"] for item in response.json()["items"]]
    assert filenames.count("via-annotation.png") == 1, (
        f"asset duplicated once per annotation: {filenames}"
    )


async def test_another_tenant_sees_none_of_it(client, seeded):
    """The endpoint takes a workspace_id, so it has to ignore a foreign one."""
    other_workspace = uuid.uuid4()
    response = await client.get(
        "/api/annotate/assets",
        params={
            "dataset_id": str(seeded["dataset_id"]),
            "workspace_id": str(seeded["workspace_id"]),
        },
        headers=_auth(other_workspace),
    )

    # TenantGuardMiddleware refuses the named workspace outright; if that ever
    # changes, an empty list is the only other acceptable answer.
    if response.status_code == 200:
        assert response.json()["items"] == [], (
            "tenant isolation breached: another workspace listed these assets"
        )
    else:
        assert response.status_code in (403, 404), response.text


async def test_an_empty_dataset_is_empty_not_an_error(client, seeded):
    response = await client.get(
        "/api/annotate/assets",
        params={"dataset_id": str(uuid.uuid4())},
        headers=_auth(seeded["workspace_id"]),
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"] == []
