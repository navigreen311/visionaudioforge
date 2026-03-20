"""Governance routes: API keys, SSO, permissions, billing, feature flags."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_current_workspace, get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.services.governance.api_keys import APIKeyService
from app.services.governance.billing import BillingService
from app.services.governance.feature_flags import FeatureFlagService
from app.services.governance.permissions import PermissionService
from app.services.governance.sso import SSOService

router = APIRouter(prefix="/governance", tags=["governance"])


# --- Request/Response Models ---

class CreateAPIKeyRequest(BaseModel):
    name: str
    scopes: list[str]
    expires_in_days: int | None = None


class UpgradePlanRequest(BaseModel):
    plan: str


class SSOLoginRequest(BaseModel):
    workspace_id: str


class OAuthCallbackRequest(BaseModel):
    provider: str
    code: str


# --- API Key Routes ---

@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: CreateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Create a new API key for the current workspace."""
    try:
        result = await APIKeyService.create_key(
            db=db,
            workspace_id=workspace.id,
            user_id=current_user.id,
            name=body.name,
            scopes=body.scopes,
            expires_in_days=body.expires_in_days,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api-keys")
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """List all active API keys for the workspace (prefix only)."""
    return await APIKeyService.list_keys(db, workspace.id)


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke an API key."""
    revoked = await APIKeyService.revoke_key(db, key_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"revoked": True}


@router.post("/api-keys/{key_id}/rotate")
async def rotate_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rotate an API key (revoke old, create new with same scopes)."""
    try:
        result = await APIKeyService.rotate_key(db, key_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- SSO Routes ---

@router.get("/sso/config")
async def get_sso_config(
    workspace: Workspace = Depends(get_current_workspace),
):
    """Get SSO configuration for the workspace."""
    return SSOService.get_sso_config(str(workspace.id))


@router.post("/sso/login")
async def initiate_sso_login(
    body: SSOLoginRequest,
):
    """Initiate SSO login flow."""
    return SSOService.initiate_sso_login(body.workspace_id)


# --- Permission Routes ---

@router.get("/permissions/{role}")
async def get_permissions(role: str):
    """Get all permissions for a given role."""
    permissions = PermissionService.get_user_permissions(role)
    return {
        "role": role,
        "permissions": permissions,
    }


# --- Billing Routes ---

@router.get("/billing/usage")
async def get_billing_usage(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Get current usage for the workspace."""
    return await BillingService.get_usage(db, workspace.id)


@router.get("/billing/dashboard")
async def get_billing_dashboard(
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Get billing dashboard with plan, usage, overage, and recommendations."""
    return await BillingService.get_billing_dashboard(db, workspace.id)


@router.post("/billing/upgrade")
async def upgrade_plan(
    body: UpgradePlanRequest,
    db: AsyncSession = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """Upgrade the workspace plan."""
    try:
        result = await BillingService.upgrade_plan(db, workspace.id, body.plan)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Feature Flag Routes ---

@router.get("/features")
async def get_features(
    workspace: Workspace = Depends(get_current_workspace),
):
    """Get enabled features for the workspace plan."""
    plan = workspace.plan.value if hasattr(workspace.plan, "value") else str(workspace.plan)
    enabled = FeatureFlagService.get_enabled_features(plan)
    return {
        "plan": plan,
        "features": enabled,
    }
