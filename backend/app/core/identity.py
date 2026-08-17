"""Identity resolution — who is calling, and which tenant do they belong to.

Used by the app-level :class:`~app.middleware.auth.AuthenticationMiddleware` and
re-exported through :mod:`app.core.deps` so route handlers never have to reason
about headers, token formats, or workspace lookup themselves.

Two credential shapes are accepted, in this order:

1. ``X-API-Key`` — machine-to-machine. The key row already carries its
   workspace, so no further lookup is needed.
2. ``Authorization: Bearer <jwt>`` — interactive sessions.

Resolution here is deliberately **I/O-free for JWTs**: the workspace comes from
the ``workspace_id`` claim and nothing else, so the middleware adds no database
round-trip to the hot path. Tokens minted before that claim existed resolve to
``workspace_id=None``; the ``get_workspace_id`` dependency in
:mod:`app.core.deps` covers them with a lookup, but only on routes that
actually need a tenant. See ``docs/auth.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
from uuid import UUID

from fastapi import status

from app.core.logging_config import get_logger
from app.core.security import decode_token

logger = get_logger("auth")

# Claim names checked, in order, for the tenant the token was issued for.
WORKSPACE_CLAIMS: tuple[str, ...] = ("workspace_id", "ws", "tenant_id")


class AuthError(Exception):
    """Raised when a request carries no usable identity.

    Carries an HTTP status so the middleware can render it without a second
    mapping table. 401 means "authenticate"; the middleware never raises 403
    here because *authorisation* is a route-level concern.
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_401_UNAUTHORIZED,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class Identity:
    """The authenticated caller, resolved once per request."""

    user_id: UUID
    workspace_id: UUID | None = None
    auth_method: str = "jwt"
    claims: dict[str, Any] = field(default_factory=dict)

    @property
    def is_tenant_scoped(self) -> bool:
        return self.workspace_id is not None


def _coerce_uuid(value: Any, *, what: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise AuthError(f"Invalid token: {what} is not a UUID") from exc


def _workspace_from_claims(claims: Mapping[str, Any]) -> UUID | None:
    for name in WORKSPACE_CLAIMS:
        raw = claims.get(name)
        if raw:
            try:
                return UUID(str(raw))
            except (TypeError, ValueError):
                raise AuthError("Invalid token: workspace claim is not a UUID")
    return None


async def _identity_from_api_key(api_key: str) -> Identity:
    from app.database import async_session_factory
    from app.services.governance.api_keys import APIKeyService

    try:
        async with async_session_factory() as session:
            info = await APIKeyService.validate_key(session, api_key)
    except AuthError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning("API key validation failed", exc_info=True)
        raise AuthError("Could not validate API key") from exc

    if not info.get("valid"):
        raise AuthError("Invalid or expired API key")

    return Identity(
        user_id=_coerce_uuid(info.get("user_id"), what="API key owner"),
        workspace_id=(
            _coerce_uuid(info["workspace_id"], what="API key workspace")
            if info.get("workspace_id")
            else None
        ),
        auth_method="api_key",
        claims={"scopes": info.get("scopes", [])},
    )


async def _identity_from_bearer(token: str) -> Identity:
    # decode_token raises HTTPException(401) on a bad signature or expiry.
    from fastapi import HTTPException

    try:
        claims = decode_token(token)
    except HTTPException as exc:
        raise AuthError(str(exc.detail), status_code=exc.status_code) from exc

    if claims.get("type") == "refresh":
        raise AuthError("Refresh tokens cannot be used to call the API")

    return Identity(
        user_id=_coerce_uuid(claims.get("sub"), what="subject"),
        workspace_id=_workspace_from_claims(claims),
        auth_method="jwt",
        claims=dict(claims),
    )


async def resolve_identity(headers: Mapping[str, str]) -> Identity:
    """Resolve the caller from request headers, or raise :class:`AuthError`.

    *headers* must be case-insensitive (Starlette's ``Headers`` is).
    """
    api_key = headers.get("x-api-key")
    if api_key:
        return await _identity_from_api_key(api_key)

    authorization = headers.get("authorization") or ""
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise AuthError(
            "Missing authentication: provide an Authorization: Bearer "
            "<token> header or an X-API-Key header"
        )

    return await _identity_from_bearer(credentials.strip())
