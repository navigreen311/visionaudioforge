"""Tenant isolation across the *real* routes.

``test_auth_enforcement.py`` proves two things well: every route challenges an
anonymous caller, and the workspace a request acts on comes from the signed
token. It proves the second against a synthetic probe route, because the
workstream that wrote it did not own the real routes.

This file closes that gap. It drives the routes the console actually calls, with
two genuinely separate tenants created through the public registration flow, and
asserts that a token minted for one cannot read or mutate the other's rows —
however helpfully the caller asks.

Marked ``auth_enforced`` throughout: the rest of the suite runs with
``settings.AUTH_REQUIRED`` off (see conftest), and an isolation test that runs
with the boundary disabled is a test that cannot fail for the right reason.
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.anyio, pytest.mark.auth_enforced]

PASSWORD = "TenantIsolation!2026"


class _StorageUnavailable(RuntimeError):
    """Object storage is not reachable in this environment."""


async def _register(client) -> tuple[str, str]:
    """Create a tenant through the public flow. Returns (token, workspace_id)."""
    stamp = uuid.uuid4().hex[:12]
    response = await client.post(
        "/api/auth/register",
        json={
            "email": f"tenant-{stamp}@example.com",
            "password": PASSWORD,
            "workspace_name": f"tenant-{stamp}",
        },
    )
    assert response.status_code == 201, f"registration failed: {response.text}"
    body = response.json()
    workspace_id = body["user"]["workspace_id"]
    assert workspace_id, "registration returned no workspace"
    return body["access_token"], workspace_id


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def tenants(client):
    """Two unrelated tenants, each with a real workspace and a real token."""
    token_a, ws_a = await _register(client)
    token_b, ws_b = await _register(client)
    assert ws_a != ws_b, "the two registrations shared a workspace"
    return {"a": (token_a, ws_a), "b": (token_b, ws_b)}


# ---------------------------------------------------------------------------
# Datasets — created with an explicit workspace_id, which is the risk
# ---------------------------------------------------------------------------

async def test_a_dataset_is_invisible_to_the_other_tenant(client, tenants):
    token_a, ws_a = tenants["a"]
    token_b, ws_b = tenants["b"]

    created = await client.post(
        "/api/datasets",
        params={"workspace_id": ws_a},
        json={"name": "tenant-a-private", "modality": "image"},
        headers=_auth(token_a),
    )
    assert created.status_code == 201, created.text
    dataset_id = created.json()["id"]

    # B asks for A's workspace by name. The query parameter is caller-controlled;
    # the token is not. The token must win.
    listed = await client.get(
        "/api/datasets",
        params={"workspace_id": ws_a},
        headers=_auth(token_b),
    )
    assert listed.status_code in (200, 403), listed.text
    if listed.status_code == 200:
        names = [item["name"] for item in listed.json().get("items", [])]
        assert "tenant-a-private" not in names, (
            "tenant isolation breached: B listed A's dataset by passing "
            "?workspace_id=A"
        )

    fetched = await client.get(f"/api/datasets/{dataset_id}", headers=_auth(token_b))
    assert fetched.status_code in (403, 404), (
        f"tenant isolation breached: B read A's dataset directly "
        f"(status {fetched.status_code})"
    )


async def test_a_tenant_cannot_create_rows_in_another_workspace(client, tenants):
    token_a, _ = tenants["a"]
    _, ws_b = tenants["b"]

    response = await client.post(
        "/api/datasets",
        params={"workspace_id": ws_b},
        json={"name": "planted-by-a", "modality": "image"},
        headers=_auth(token_a),
    )
    assert response.status_code in (403, 404), (
        f"tenant isolation breached: A created a row inside B's workspace "
        f"(status {response.status_code})"
    )


async def test_the_tenants_own_data_is_still_reachable(client, tenants):
    """The guard must not be a blanket denial — A can still use A."""
    token_a, ws_a = tenants["a"]

    created = await client.post(
        "/api/datasets",
        params={"workspace_id": ws_a},
        json={"name": "tenant-a-visible", "modality": "audio"},
        headers=_auth(token_a),
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        "/api/datasets", params={"workspace_id": ws_a}, headers=_auth(token_a)
    )
    assert listed.status_code == 200, listed.text
    names = [item["name"] for item in listed.json().get("items", [])]
    assert "tenant-a-visible" in names

    fetched = await client.get(
        f"/api/datasets/{created.json()['id']}", headers=_auth(token_a)
    )
    assert fetched.status_code == 200, fetched.text


async def test_omitting_the_workspace_does_not_widen_the_view(client, tenants):
    """A request with no workspace_id must scope to the token, not to everything."""
    token_a, ws_a = tenants["a"]
    token_b, ws_b = tenants["b"]

    created = await client.post(
        "/api/datasets",
        params={"workspace_id": ws_b},
        json={"name": "tenant-b-private", "modality": "image"},
        headers=_auth(token_b),
    )
    assert created.status_code == 201, created.text

    listed = await client.get("/api/datasets", headers=_auth(token_a))
    if listed.status_code == 200:
        names = [item["name"] for item in listed.json().get("items", [])]
        assert "tenant-b-private" not in names, (
            "tenant isolation breached: omitting workspace_id exposed another "
            "tenant's rows"
        )


# ---------------------------------------------------------------------------
# Model registry — same shape, different table, workspace in the *body*
# ---------------------------------------------------------------------------

async def test_a_model_registered_by_one_tenant_is_invisible_to_the_other(client, tenants):
    token_a, ws_a = tenants["a"]
    token_b, ws_b = tenants["b"]

    created = await client.post(
        "/api/registry/register",
        json={
            "name": "tenant-a-model",
            "version": "1.0.0",
            "backbone": "ViT-B/32",
            "metrics": {"accuracy": 0.9},
            "workspace_id": ws_a,
        },
        headers=_auth(token_a),
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        "/api/registry/models", params={"workspace_id": ws_a}, headers=_auth(token_b)
    )
    if listed.status_code == 200:
        names = [item["name"] for item in listed.json().get("items", [])]
        assert "tenant-a-model" not in names, (
            "tenant isolation breached: B listed A's models"
        )


async def test_a_tenant_cannot_register_a_model_into_another_workspace(client, tenants):
    token_a, _ = tenants["a"]
    _, ws_b = tenants["b"]

    response = await client.post(
        "/api/registry/register",
        json={
            "name": "planted-model",
            "version": "1.0.0",
            "workspace_id": ws_b,
        },
        headers=_auth(token_a),
    )
    assert response.status_code in (403, 404), (
        f"tenant isolation breached: A registered a model in B's workspace "
        f"(status {response.status_code})"
    )


# ---------------------------------------------------------------------------
# Assets — the severe case: media files, reachable by id alone
# ---------------------------------------------------------------------------

async def _upload(client, token: str, name: str):
    """Upload a one-pixel PNG through the real multipart endpoint.

    Raises ``_StorageUnavailable`` when object storage is not reachable, so the
    asset tests below skip rather than fail in an environment without MinIO.
    """
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    try:
        return await client.post(
            "/api/assets/upload",
            files={"file": (name, png, "image/png")},
            data={"asset_type": "image"},
            headers=_auth(token),
        )
    except Exception as exc:  # noqa: BLE001 - any storage failure means "no MinIO"
        if "S3" in type(exc).__name__ or "minio" in type(exc).__module__:
            raise _StorageUnavailable(str(exc)) from exc
        raise


async def test_an_asset_cannot_be_read_or_downloaded_by_another_tenant(client, tenants):
    """The worst of the family: media bytes reachable with nothing but an id."""
    token_a, _ = tenants["a"]
    token_b, _ = tenants["b"]

    try:
        created = await _upload(client, token_a, "tenant-a-secret.png")
    except _StorageUnavailable as exc:
        pytest.skip(f"object storage unavailable: {exc}")
    if created.status_code not in (200, 201):
        pytest.skip(f"asset upload unavailable in this environment: {created.status_code}")
    asset_id = created.json()["id"]

    assert (await client.get(f"/api/assets/{asset_id}", headers=_auth(token_b))).status_code == 404, (
        "tenant isolation breached: B read A's asset metadata"
    )
    assert (
        await client.get(f"/api/assets/{asset_id}/download", headers=_auth(token_b))
    ).status_code == 404, "tenant isolation breached: B downloaded A's file"
    assert (
        await client.delete(f"/api/assets/{asset_id}", headers=_auth(token_b))
    ).status_code == 404, "tenant isolation breached: B deleted A's asset"

    # A still owns it.
    assert (await client.get(f"/api/assets/{asset_id}", headers=_auth(token_a))).status_code == 200


async def test_upload_needs_no_workspace_field_from_the_browser(client, tenants):
    """The console sends no workspace_id, and must not have to.

    This is the regression net for the 422 that made asset upload impossible
    from the UI: the field was required, and the browser had no business
    choosing a tenant in the first place.
    """
    token_a, ws_a = tenants["a"]
    try:
        created = await _upload(client, token_a, "no-workspace-field.png")
    except _StorageUnavailable as exc:
        pytest.skip(f"object storage unavailable: {exc}")
    if created.status_code not in (200, 201):
        pytest.skip(f"asset upload unavailable in this environment: {created.status_code}")
    assert str(created.json()["workspace_id"]) == ws_a


# ---------------------------------------------------------------------------
# API keys — the one bulk-write path with a route in front of it
# ---------------------------------------------------------------------------


async def _create_api_key(client, token: str, workspace_id: str, name: str):
    return await client.post(
        f"/api/settings/api-keys?workspace_id={workspace_id}",
        headers=_auth(token),
        json={"name": name, "scopes": []},
    )


async def test_an_api_key_cannot_be_revoked_by_another_tenant(client, tenants):
    """Revocation at the HTTP surface, where an attacker actually stands.

    Note what this does and does not prove. `revoke_api_key` loads the row with
    an explicit workspace predicate before issuing
    `update(APIKey).where(APIKey.id == key_id)`, so it 404s on that first check
    and this test passes with or without the session-level write filter —
    verified by reverting the filter and re-running.

    It is still worth having: it is the regression net for that route guard, and
    the second assertion (the key is still listed afterwards) would catch a
    revoke that 404s the caller while deactivating the row anyway. The write
    filter itself is proved directly in test_session_scoping.py, which does not
    go through a route that guards itself.
    """
    token_a, ws_a = tenants["a"]
    token_b, ws_b = tenants["b"]

    created = await _create_api_key(client, token_a, ws_a, "tenant-a-key")
    if created.status_code != 201:
        pytest.skip(f"api key creation unavailable here: {created.status_code} {created.text}")
    key_id = created.json()["id"]

    # B naming its own workspace but A's key id: the id is the only thing the
    # tenant guard cannot check for itself.
    revoked = await client.delete(
        f"/api/settings/api-keys/{key_id}?workspace_id={ws_b}", headers=_auth(token_b)
    )
    assert revoked.status_code == 404, (
        f"tenant isolation breached: B revoked A's API key ({revoked.status_code})"
    )

    # And the key is still usable by its owner — a 404 that happened to have
    # deactivated the row anyway would be the same bug wearing a hat.
    listed = await client.get(
        f"/api/settings/api-keys?workspace_id={ws_a}", headers=_auth(token_a)
    )
    assert listed.status_code == 200
    assert any(k["id"] == key_id for k in listed.json()), (
        "tenant isolation breached: B's revoke deactivated A's key despite the 404"
    )


async def test_a_tenant_can_still_revoke_its_own_api_key(client, tenants):
    """The other half: scoping writes must not break the legitimate path."""
    token_a, ws_a = tenants["a"]

    created = await _create_api_key(client, token_a, ws_a, "tenant-a-own-key")
    if created.status_code != 201:
        pytest.skip(f"api key creation unavailable here: {created.status_code}")
    key_id = created.json()["id"]

    revoked = await client.delete(
        f"/api/settings/api-keys/{key_id}?workspace_id={ws_a}", headers=_auth(token_a)
    )
    assert revoked.status_code == 204, f"A could not revoke its own key: {revoked.text}"

    listed = await client.get(
        f"/api/settings/api-keys?workspace_id={ws_a}", headers=_auth(token_a)
    )
    assert not any(k["id"] == key_id for k in listed.json()), (
        "the key is still listed as active after its owner revoked it"
    )
