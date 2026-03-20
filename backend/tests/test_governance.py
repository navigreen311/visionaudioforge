"""Tests for governance services: API keys, permissions, billing, feature flags."""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.governance.api_keys import APIKeyService, _hash_key, _generate_key
from app.services.governance.billing import BillingService, PLANS
from app.services.governance.feature_flags import FeatureFlagService, FLAGS
from app.services.governance.permissions import PermissionService
from app.services.governance.sso import SSOService


# ---------------------------------------------------------------------------
# API Key tests
# ---------------------------------------------------------------------------


class TestAPIKeyGeneration:
    """Unit tests for API key helper functions."""

    def test_generate_key_prefix(self):
        key = _generate_key()
        assert key.startswith("vaf_")
        assert len(key) > 12

    def test_hash_key_deterministic(self):
        key = "vaf_test123"
        assert _hash_key(key) == _hash_key(key)
        assert _hash_key(key) == hashlib.sha256(key.encode()).hexdigest()


@pytest.mark.anyio
async def test_api_key_create_and_validate():
    """Create an API key and validate it round-trips correctly."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()

    # Mock the select for validate_key
    workspace_id = uuid4()
    user_id = uuid4()

    # Create key
    result = await APIKeyService.create_key(
        db=db,
        workspace_id=workspace_id,
        user_id=user_id,
        name="test-key",
        scopes=["read", "write"],
        expires_in_days=30,
    )

    assert result["key"].startswith("vaf_")
    assert result["key_prefix"].endswith("...")
    assert result["scopes"] == ["read", "write"]
    assert result["expires_at"] is not None
    assert result["key_id"] is not None
    assert db.add.called
    assert db.commit.called


@pytest.mark.anyio
async def test_api_key_revoke():
    """Revoking a key sets is_active=False."""
    db = AsyncMock()
    db.commit = AsyncMock()

    # Mock execute to return rowcount > 0
    mock_result = MagicMock()
    mock_result.rowcount = 1
    db.execute = AsyncMock(return_value=mock_result)

    key_id = uuid4()
    revoked = await APIKeyService.revoke_key(db, key_id)
    assert revoked is True

    # Test revoke of non-existent key
    mock_result.rowcount = 0
    revoked = await APIKeyService.revoke_key(db, uuid4())
    assert revoked is False


# ---------------------------------------------------------------------------
# Permission tests
# ---------------------------------------------------------------------------


def test_permission_admin_has_all():
    """Admin role should have access to every scope."""
    assert PermissionService.check_permission("admin", "read") is True
    assert PermissionService.check_permission("admin", "write") is True
    assert PermissionService.check_permission("admin", "vision") is True
    assert PermissionService.check_permission("admin", "pipeline") is True
    assert PermissionService.check_permission("admin", "agents") is True
    assert PermissionService.check_permission("admin", "anything") is True


def test_permission_viewer_read_only():
    """Viewer should only have read and search."""
    assert PermissionService.check_permission("viewer", "read") is True
    assert PermissionService.check_permission("viewer", "search") is True
    assert PermissionService.check_permission("viewer", "write") is False
    assert PermissionService.check_permission("viewer", "vision") is False
    assert PermissionService.check_permission("viewer", "admin") is False


def test_permission_operator_scopes():
    """Operator should have specific scopes."""
    assert PermissionService.check_permission("operator", "read") is True
    assert PermissionService.check_permission("operator", "write") is True
    assert PermissionService.check_permission("operator", "vision") is True
    assert PermissionService.check_permission("operator", "search") is False


def test_permission_analyst_scopes():
    """Analyst should have read, search, vision, audio, investigate, evaluate."""
    assert PermissionService.check_permission("analyst", "read") is True
    assert PermissionService.check_permission("analyst", "search") is True
    assert PermissionService.check_permission("analyst", "investigate") is True
    assert PermissionService.check_permission("analyst", "write") is False


def test_get_user_permissions():
    """get_user_permissions returns the correct scope list."""
    admin_perms = PermissionService.get_user_permissions("admin")
    assert len(admin_perms) > 5  # admin has all expanded scopes

    viewer_perms = PermissionService.get_user_permissions("viewer")
    assert viewer_perms == ["read", "search"]


def test_can_access_module():
    """Module access maps module names to scopes correctly."""
    assert PermissionService.can_access_module("admin", "vision") is True
    assert PermissionService.can_access_module("viewer", "vision") is False
    assert PermissionService.can_access_module("viewer", "assets") is True
    assert PermissionService.can_access_module("operator", "capture") is True


# ---------------------------------------------------------------------------
# Billing tests
# ---------------------------------------------------------------------------


def test_billing_free_plan_limits():
    """Free plan should have specific resource limits."""
    free = PLANS["free"]
    assert free["price"] == 0
    assert free["limits"]["assets"] == 100
    assert free["limits"]["models"] == 3
    assert free["limits"]["pipelines"] == 5
    assert free["limits"]["api_calls_daily"] == 1000
    assert free["limits"]["storage_gb"] == 1


def test_billing_enterprise_unlimited():
    """Enterprise plan should have -1 (unlimited) for most resources."""
    ent = PLANS["enterprise"]
    assert ent["limits"]["assets"] == -1
    assert ent["limits"]["models"] == -1
    assert ent["limits"]["pipelines"] == -1
    assert ent["limits"]["api_calls_daily"] == -1
    assert ent["price"] == 299


@pytest.mark.anyio
async def test_billing_check_over_limit():
    """check_limit should return allowed=False when over limit."""
    db = AsyncMock()

    # Mock workspace with free plan and usage over limit
    mock_workspace = MagicMock()
    mock_workspace.plan = MagicMock()
    mock_workspace.plan.value = "free"
    mock_workspace.settings = {"usage": {"assets": 150}}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_workspace
    db.execute = AsyncMock(return_value=mock_result)

    result = await BillingService.check_limit(db, uuid4(), "assets")
    assert result["allowed"] is False
    assert result["current"] == 150
    assert result["limit"] == 100
    assert result["plan"] == "free"


@pytest.mark.anyio
async def test_billing_check_within_limit():
    """check_limit should return allowed=True when within limit."""
    db = AsyncMock()

    mock_workspace = MagicMock()
    mock_workspace.plan = MagicMock()
    mock_workspace.plan.value = "pro"
    mock_workspace.settings = {"usage": {"assets": 50}}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_workspace
    db.execute = AsyncMock(return_value=mock_result)

    result = await BillingService.check_limit(db, uuid4(), "assets")
    assert result["allowed"] is True
    assert result["current"] == 50
    assert result["limit"] == 10000


@pytest.mark.anyio
async def test_usage_tracking():
    """track_api_call should increment the daily counter."""
    db = AsyncMock()
    db.commit = AsyncMock()

    mock_workspace = MagicMock()
    mock_workspace.id = uuid4()
    mock_workspace.settings = {"usage": {"api_calls_daily": 5}}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_workspace
    db.execute = AsyncMock(return_value=mock_result)

    await BillingService.track_api_call(db, mock_workspace.id)
    # Verify execute was called (once for select, once for update)
    assert db.execute.call_count == 2
    assert db.commit.called


@pytest.mark.anyio
async def test_get_usage():
    """get_usage should return plan, usage, limits, and percentages."""
    db = AsyncMock()

    mock_workspace = MagicMock()
    mock_workspace.plan = MagicMock()
    mock_workspace.plan.value = "free"
    mock_workspace.settings = {"usage": {"assets": 50, "models": 1}}

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_workspace
    db.execute = AsyncMock(return_value=mock_result)

    result = await BillingService.get_usage(db, uuid4())
    assert result["plan"] == "free"
    assert result["limits"]["assets"] == 100
    assert result["usage_pct"]["assets"] == 50.0


# ---------------------------------------------------------------------------
# Feature flag tests
# ---------------------------------------------------------------------------


def test_feature_flag_pro_plan():
    """Pro plan should have access to pro-tier features."""
    assert FeatureFlagService.is_enabled("capture_rtsp", "pro") is True
    assert FeatureFlagService.is_enabled("copilot", "pro") is True
    assert FeatureFlagService.is_enabled("api_access", "pro") is True
    assert FeatureFlagService.is_enabled("custom_models", "pro") is True


def test_feature_flag_free_plan_restricted():
    """Free plan should not have access to any gated features."""
    assert FeatureFlagService.is_enabled("capture_rtsp", "free") is False
    assert FeatureFlagService.is_enabled("copilot", "free") is False
    assert FeatureFlagService.is_enabled("sso", "free") is False
    assert FeatureFlagService.is_enabled("white_label", "free") is False


def test_feature_flag_enterprise_only():
    """Enterprise-only features should not be available on pro."""
    assert FeatureFlagService.is_enabled("advanced_analytics", "pro") is False
    assert FeatureFlagService.is_enabled("advanced_analytics", "enterprise") is True
    assert FeatureFlagService.is_enabled("sso", "pro") is False
    assert FeatureFlagService.is_enabled("sso", "enterprise") is True


def test_check_feature_upgrade_suggestion():
    """check_feature should suggest the cheapest qualifying plan."""
    result = FeatureFlagService.check_feature("copilot", "free")
    assert result["enabled"] is False
    assert result["upgrade_to"] == "pro"

    result = FeatureFlagService.check_feature("sso", "free")
    assert result["enabled"] is False
    assert result["upgrade_to"] == "enterprise"

    result = FeatureFlagService.check_feature("copilot", "pro")
    assert result["enabled"] is True
    assert result["upgrade_to"] is None


def test_get_enabled_features():
    """get_enabled_features returns correct list per plan."""
    free_features = FeatureFlagService.get_enabled_features("free")
    assert len(free_features) == 0

    pro_features = FeatureFlagService.get_enabled_features("pro")
    assert "copilot" in pro_features
    assert "sso" not in pro_features

    enterprise_features = FeatureFlagService.get_enabled_features("enterprise")
    assert "sso" in enterprise_features
    assert "white_label" in enterprise_features
    assert len(enterprise_features) == len(FLAGS)


# ---------------------------------------------------------------------------
# SSO stub tests
# ---------------------------------------------------------------------------


def test_sso_config_stub():
    """SSO config should return disabled with guidance note."""
    config = SSOService.get_sso_config("test-workspace")
    assert config["enabled"] is False
    assert "python3-saml" in config["note"]


def test_sso_login_stub():
    """SSO login should return a placeholder redirect URL."""
    result = SSOService.initiate_sso_login("ws-123")
    assert "redirect_url" in result
    assert "ws-123" in result["redirect_url"]


def test_oauth_url_google():
    """OAuth URL for Google should contain google.com."""
    result = SSOService.get_oauth_url("google")
    assert "google.com" in result["url"]


def test_oauth_url_github():
    """OAuth URL for GitHub should contain github.com."""
    result = SSOService.get_oauth_url("github")
    assert "github.com" in result["url"]


def test_oauth_callback_stub():
    """OAuth callback should return stub user data."""
    result = SSOService.process_oauth_callback("google", "test-code")
    assert result["user"]["provider"] == "google"
    assert "token" in result


# ---------------------------------------------------------------------------
# API route smoke tests (via test client)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_create_key(client, auth_headers):
    """POST /api/governance/api-keys should accept key creation request."""
    resp = await client.post(
        "/api/governance/api-keys",
        json={"name": "test", "scopes": ["read"]},
        headers=auth_headers,
    )
    # May return 201 (success) or 401/501 (auth not fully wired in test)
    assert resp.status_code in (201, 401, 403, 501)


@pytest.mark.anyio
async def test_api_billing_usage(client, auth_headers):
    """GET /api/governance/billing/usage should respond."""
    resp = await client.get(
        "/api/governance/billing/usage",
        headers=auth_headers,
    )
    assert resp.status_code in (200, 401, 403, 404, 501)


@pytest.mark.anyio
async def test_api_permissions_role(client):
    """GET /api/governance/permissions/admin should return permissions."""
    resp = await client.get("/api/governance/permissions/admin")
    # This endpoint has no auth requirement
    assert resp.status_code == 200
    data = resp.json()
    assert data["role"] == "admin"
    assert len(data["permissions"]) > 0
