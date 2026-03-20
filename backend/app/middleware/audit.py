"""Audit middleware: logs every request to the audit_logs table (non-blocking)."""

import asyncio
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.database import async_session_factory
from app.models.audit_log import AuditLog


async def _write_audit_log(
    user_id: str | None,
    action: str,
    resource_type: str,
    ip_address: str | None,
) -> None:
    """Persist an audit log entry in a separate DB session (background)."""
    async with async_session_factory() as session:
        log = AuditLog(
            user_id=UUID(user_id) if user_id else None,
            action=action,
            resource_type=resource_type,
            ip_address=ip_address,
        )
        session.add(log)
        await session.commit()


class AuditMiddleware(BaseHTTPMiddleware):
    """Log user_id, HTTP method, path, and client IP after each response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Extract user_id from request state if auth dependency set it,
        # otherwise try to parse the Authorization header without blocking.
        user_id: str | None = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_token

                payload = decode_token(auth_header[7:])
                user_id = payload.get("sub")
            except Exception:
                pass

        # Fire-and-forget background task so audit logging never blocks the response.
        asyncio.ensure_future(
            _write_audit_log(
                user_id=user_id,
                action=request.method,
                resource_type=request.url.path,
                ip_address=request.client.host if request.client else None,
            )
        )

        return response
