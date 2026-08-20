"""Pipelines can actually be saved, and read back the same.

No pipeline could be persisted by any client. Both write routes passed
``description=`` to a ``Pipeline`` model that declares no such column::

    TypeError: 'description' is an invalid keyword argument for Pipeline

so ``POST /api/pipeline/create`` and ``POST /api/pipeline/save`` both answered
500. The builder could not save, and neither could an API client.

It survived a 1600-test suite because nothing in it had ever saved one. The
pipeline tests exercised validation, node registration and the engine — every
part of the feature except the write. A 500 on the primary write path of a
headline feature should not need a browser to find, so these drive the real
routes against a real database.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.tenancy import unscoped
from app.database import async_session_factory
from app.models.pipeline import Pipeline
from app.models.workspace import Workspace

pytestmark = pytest.mark.anyio

WORKSPACE = uuid.UUID("cccccccc-0000-0000-0000-00000000000c")

# The smallest definition the engine calls valid: one source node whose
# required inputs are all supplied as params.
MINIMAL_DEFINITION = {
    "nodes": [
        {"id": "input_1", "type": "input_image", "params": {"path": "probe.png"}}
    ],
    "edges": [],
}


@pytest.fixture
async def workspace():
    async with async_session_factory() as db:
        with unscoped():  # setup, not the call under test
            if await db.get(Workspace, WORKSPACE) is None:
                db.add(
                    Workspace(
                        id=WORKSPACE,
                        name="pipeline-persistence",
                        slug=f"pipeline-persistence-{uuid.uuid4().hex[:8]}",
                    )
                )
                await db.commit()
    yield WORKSPACE


async def _cleanup(pipeline_id) -> None:
    async with async_session_factory() as db:
        with unscoped():
            row = await db.get(Pipeline, pipeline_id)
            if row is not None:
                await db.delete(row)
                await db.commit()


# ---------------------------------------------------------------------------
# The write path
# ---------------------------------------------------------------------------


async def test_create_persists_a_pipeline(client, workspace):
    """POST /api/pipeline/create writes a row and returns it."""
    response = await client.post(
        "/api/pipeline/create",
        json={
            "name": "persistence probe",
            "description": "written by the persistence test",
            "definition": MINIMAL_DEFINITION,
            "workspace_id": str(workspace),
        },
    )

    assert response.status_code == 201, (
        f"pipeline create failed: {response.status_code} {response.text}"
    )
    body = response.json()
    assert body["name"] == "persistence probe"
    assert body["workspace_id"] == str(workspace)

    try:
        # The row is really there, not just echoed back from the request.
        async with async_session_factory() as db:
            with unscoped():
                stored = await db.get(Pipeline, uuid.UUID(body["id"]))
                assert stored is not None, "create returned 201 but wrote no row"
                assert stored.name == "persistence probe"
                assert stored.definition == MINIMAL_DEFINITION
    finally:
        await _cleanup(uuid.UUID(body["id"]))


async def test_save_persists_a_pipeline(client, workspace):
    """POST /api/pipeline/save — the second write path, broken the same way."""
    response = await client.post(
        "/api/pipeline/save",
        json={
            "name": "save probe",
            "description": "saved by the persistence test",
            "definition": MINIMAL_DEFINITION,
            "workspace_id": str(workspace),
        },
    )

    assert response.status_code == 201, (
        f"pipeline save failed: {response.status_code} {response.text}"
    )
    pipeline_id = uuid.UUID(response.json()["id"])
    try:
        async with async_session_factory() as db:
            with unscoped():
                assert await db.get(Pipeline, pipeline_id) is not None
    finally:
        await _cleanup(pipeline_id)


async def test_a_saved_pipeline_reads_back_with_its_description(client, workspace):
    """The response model promises a description; a read must actually carry it.

    `PipelineRead.description` is part of the published contract. Accepting the
    field on write and returning null on read would be the same defect wearing
    a different hat.
    """
    description = "keeps its description across a round trip"
    created = await client.post(
        "/api/pipeline/create",
        json={
            "name": "round trip probe",
            "description": description,
            "definition": MINIMAL_DEFINITION,
            "workspace_id": str(workspace),
        },
    )
    assert created.status_code == 201, created.text
    pipeline_id = created.json()["id"]

    try:
        assert created.json()["description"] == description, (
            "create accepted a description and returned a different one"
        )

        listed = await client.get(f"/api/pipeline/list?workspace_id={workspace}")
        assert listed.status_code == 200, listed.text
        mine = [p for p in listed.json()["items"] if p["id"] == pipeline_id]
        assert mine, "the saved pipeline is not in the list"
        assert mine[0]["description"] == description, (
            "the description did not survive being written and read back"
        )
    finally:
        await _cleanup(uuid.UUID(pipeline_id))


async def test_create_without_a_description_is_still_valid(client, workspace):
    """The console sends only name and definition — that must keep working."""
    response = await client.post(
        "/api/pipeline/create",
        json={
            "name": "no description probe",
            "definition": MINIMAL_DEFINITION,
            "workspace_id": str(workspace),
        },
    )
    assert response.status_code == 201, response.text
    pipeline_id = uuid.UUID(response.json()["id"])
    try:
        assert response.json()["description"] is None
    finally:
        await _cleanup(pipeline_id)


async def test_a_shipped_template_can_be_saved(client, workspace):
    """The templates are the definitions users start from.

    Saving one exercises the write path with a real multi-node graph rather
    than the minimal probe above, and would catch a template whose wiring stops
    validating.
    """
    from app.services.pipeline.templates import PIPELINE_TEMPLATES

    name, template = next(iter(PIPELINE_TEMPLATES.items()))
    definition = template.get("definition", template)

    response = await client.post(
        "/api/pipeline/create",
        json={
            "name": f"template: {name}",
            "definition": definition,
            "workspace_id": str(workspace),
        },
    )
    assert response.status_code == 201, (
        f"the shipped '{name}' template could not be saved: "
        f"{response.status_code} {response.text}"
    )
    await _cleanup(uuid.UUID(response.json()["id"]))


async def test_every_shipped_template_validates():
    """A template that cannot validate is one nobody can use.

    Guards the wiring in `_build_definition`: every required input is connected
    to an earlier node that publishes that port. Hard-coded "output" -> "input"
    edges used to make every template fail validation.
    """
    from app.services.pipeline.engine import PipelineEngine
    from app.services.pipeline.templates import PIPELINE_TEMPLATES

    engine = PipelineEngine()
    invalid = {}
    for name, template in PIPELINE_TEMPLATES.items():
        result = engine.validate_pipeline(template.get("definition", template))
        if not result["valid"]:
            invalid[name] = result["errors"]

    assert not invalid, f"shipped templates that do not validate: {invalid}"
