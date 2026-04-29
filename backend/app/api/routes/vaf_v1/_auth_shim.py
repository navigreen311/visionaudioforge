"""Auth dependency shim for the WS11 intel routers.

WS10 owns the real bearer-token auth dependency at
``app/api/deps/vaf_auth.py``. Until WS10 lands, this module exposes a
``vaf_auth`` callable that raises 401 on missing/empty Authorization
headers but otherwise lets the request through. Once WS10 merges, this
module re-exports the real dependency from ``app.api.deps.vaf_auth``.

Tests override the dependency via ``app.dependency_overrides`` — see
``tests/api/vaf_v1/_test_auth.py``.

Do NOT create a competing ``vaf_auth.py`` under ``app/api/deps/`` — that
file is WS10's territory.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

try:
    # Once WS10 has merged, prefer the real dependency.
    from app.api.deps.vaf_auth import vaf_auth as _real_vaf_auth  # type: ignore

    vaf_auth = _real_vaf_auth
except Exception:  # pragma: no cover — exercised pre-merge
    async def vaf_auth(authorization: str | None = Header(default=None)) -> str:
        """Bearer-token gate. Replaced by WS10's real dependency post-merge."""
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid bearer token",
            )
        return authorization.split(" ", 1)[1].strip()
