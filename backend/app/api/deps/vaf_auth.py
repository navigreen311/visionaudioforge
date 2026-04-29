"""Bearer-token auth dependency for the VAF v1 mock API surface.

The PAF integration spec authenticates via ``Authorization: Bearer ${VAF_API_KEY}``.
For this mock service, any non-empty bearer token is accepted; the dependency
exists primarily so the contract is honored end-to-end. Real auth is out of
scope for the mock.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)


async def require_vaf_bearer(
    authorization: Optional[str] = Header(default=None),
) -> str:
    """Validate the ``Authorization: Bearer <token>`` header.

    Returns the token string on success. Raises 401 if the header is missing
    or malformed. Any non-empty token is accepted (mock service).
    """
    if not authorization:
        logger.warning("VAF v1: request missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token must not be empty",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
