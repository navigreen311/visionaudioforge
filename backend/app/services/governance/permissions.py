"""Scoped permissions: role-based access control with granular scopes."""

from typing import Callable

from fastapi import Depends, HTTPException, status

from app.models.user import User


PERMISSION_MATRIX: dict[str, list[str]] = {
    "admin": ["*"],
    "operator": ["read", "write", "vision", "audio", "capture", "alerts", "agents"],
    "analyst": ["read", "vision", "audio", "search", "investigate", "evaluate"],
    "viewer": ["read", "search"],
}

# Module-to-scope mapping
MODULE_SCOPE_MAP: dict[str, str] = {
    "vision": "vision",
    "audio": "audio",
    "search": "search",
    "pipeline": "pipeline",
    "agents": "agents",
    "capture": "capture",
    "alerts": "alerts",
    "investigation": "investigate",
    "evaluation": "evaluate",
    "assets": "read",
    "datasets": "read",
    "models": "read",
}


class PermissionService:
    """Granular scope-based permission checking."""

    @staticmethod
    def check_permission(user_role: str, required_scope: str) -> bool:
        """Check if a role grants the required scope."""
        scopes = PERMISSION_MATRIX.get(user_role, [])
        if "*" in scopes:
            return True
        return required_scope in scopes

    @staticmethod
    def get_user_permissions(role: str) -> list[str]:
        """Return all scopes granted to a role."""
        scopes = PERMISSION_MATRIX.get(role, [])
        if "*" in scopes:
            # Expand wildcard to all known scopes
            all_scopes = set()
            for role_scopes in PERMISSION_MATRIX.values():
                for s in role_scopes:
                    if s != "*":
                        all_scopes.add(s)
            return sorted(all_scopes)
        return list(scopes)

    @staticmethod
    def can_access_module(user_role: str, module: str) -> bool:
        """Check if a role can access a given module."""
        scope = MODULE_SCOPE_MAP.get(module)
        if scope is None:
            return False
        return PermissionService.check_permission(user_role, scope)


def require_scope(scope: str) -> Callable:
    """FastAPI dependency that checks if the current user has a scope.

    Usage: Depends(require_scope("vision"))
    """
    from app.core.deps import get_current_user

    async def _check_scope(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not PermissionService.check_permission(current_user.role, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Scope '{scope}' not granted to role '{current_user.role}'",
            )
        return current_user

    return _check_scope
