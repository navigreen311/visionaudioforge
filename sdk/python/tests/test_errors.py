"""Error paths: every mapped status raises its own exception type.

The original suite covered 401, 404 and 500. Validation (422) and rate limiting
(429) were untested, as was the behaviour when a server returns a non-JSON
error body — which is what a proxy or gateway sends, so it is exactly the case
a client is most likely to hit in production.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from visionaudioforge import VAFClient
from visionaudioforge.exceptions import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ServerError,
    VAFError,
    ValidationError,
)

BASE = "http://localhost:8000"
HEALTH = f"{BASE}/api/v1/health"


@pytest.fixture
async def client():
    async with VAFClient(base_url=BASE, api_key="k") as c:
        yield c


@respx.mock
@pytest.mark.parametrize(
    ("status", "exc"),
    [
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (422, ValidationError),
        (429, RateLimitError),
        (500, ServerError),
    ],
)
async def test_status_codes_map_to_their_exception(client, status, exc):
    respx.mock.get(HEALTH).mock(
        return_value=httpx.Response(status, json={"detail": "boom"})
    )

    with pytest.raises(exc) as info:
        await client.health()

    assert info.value.status_code == status
    assert "boom" in str(info.value)


@respx.mock
async def test_unmapped_status_falls_back_to_the_base_error(client):
    respx.mock.get(HEALTH).mock(
        return_value=httpx.Response(418, json={"detail": "teapot"})
    )

    with pytest.raises(VAFError) as info:
        await client.health()

    # Not one of the mapped subclasses, but still a typed SDK error.
    assert type(info.value) is VAFError
    assert info.value.status_code == 418


@respx.mock
async def test_non_json_error_body_is_still_reported(client):
    """A gateway or proxy returns HTML, not JSON. That must not mask the error."""
    respx.mock.get(HEALTH).mock(
        return_value=httpx.Response(502, text="<html>Bad Gateway</html>")
    )

    with pytest.raises(VAFError) as info:
        await client.health()

    assert info.value.status_code == 502
    assert "Bad Gateway" in str(info.value)


@respx.mock
async def test_error_detail_is_preserved_for_inspection(client):
    """Validation errors carry a body worth showing the caller."""
    body = {"detail": [{"loc": ["body", "email"], "msg": "invalid"}]}
    respx.mock.get(HEALTH).mock(return_value=httpx.Response(422, json=body))

    with pytest.raises(ValidationError) as info:
        await client.health()

    assert info.value.detail == body


@respx.mock
async def test_204_returns_an_empty_body_rather_than_failing_to_parse(client):
    """Deletes answer 204 with no body; json() on that would raise."""
    respx.mock.delete(f"{BASE}/api/assets/a1").mock(
        return_value=httpx.Response(204)
    )
    assert await client.assets.delete("a1") is None


@respx.mock
async def test_a_failed_request_does_not_clear_a_held_token(client):
    """An expired-looking 401 must not silently log the client out."""
    client.token = "jwt-123"
    respx.mock.get(HEALTH).mock(return_value=httpx.Response(401, json={}))

    with pytest.raises(AuthenticationError):
        await client.health()

    assert client.token == "jwt-123"
