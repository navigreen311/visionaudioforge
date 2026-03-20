"""SSO/SAML and OAuth2 stubs for V1 governance."""

import os
from typing import Any


class SSOService:
    """SSO/SAML integration stubs. Full implementation requires python3-saml."""

    @staticmethod
    def get_sso_config(workspace_id: str) -> dict[str, Any]:
        """Return SSO configuration for a workspace."""
        return {
            "enabled": False,
            "provider": None,
            "metadata_url": None,
            "note": (
                "SSO requires SAML library (python3-saml). "
                "Configure SSO_METADATA_URL, SSO_ENTITY_ID in env."
            ),
        }

    @staticmethod
    def initiate_sso_login(workspace_id: str) -> dict[str, Any]:
        """Initiate SSO login flow (stub)."""
        return {
            "redirect_url": f"https://sso.example.com/saml/login?workspace={workspace_id}",
            "note": "SAML SSO not yet configured. This is a placeholder URL.",
        }

    @staticmethod
    def process_sso_callback(saml_response: str) -> dict[str, Any]:
        """Process SAML callback response (stub)."""
        return {
            "user": {
                "email": "sso-user@example.com",
                "name": "SSO User",
                "provider": "saml",
            },
            "token": "stub-sso-token",
            "note": "SSO callback processing requires python3-saml. This is a stub response.",
        }

    @staticmethod
    def get_oauth_url(provider: str) -> dict[str, str]:
        """Construct OAuth2 authorization URL for Google or GitHub."""
        urls = {
            "google": (
                "https://accounts.google.com/o/oauth2/v2/auth"
                f"?client_id={os.getenv('GOOGLE_CLIENT_ID', 'not-configured')}"
                "&response_type=code"
                "&scope=openid%20email%20profile"
                f"&redirect_uri={os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:3000/auth/callback')}"
            ),
            "github": (
                "https://github.com/login/oauth/authorize"
                f"?client_id={os.getenv('GITHUB_CLIENT_ID', 'not-configured')}"
                "&scope=read:user%20user:email"
            ),
        }
        if provider not in urls:
            return {"url": "", "error": f"Unsupported OAuth provider: {provider}"}
        return {"url": urls[provider]}

    @staticmethod
    def process_oauth_callback(provider: str, code: str) -> dict[str, Any]:
        """Process OAuth2 callback (stub)."""
        return {
            "user": {
                "email": f"oauth-user@{provider}.example.com",
                "name": f"OAuth {provider.title()} User",
                "provider": provider,
            },
            "token": f"stub-oauth-{provider}-token",
            "note": (
                f"OAuth {provider} callback processing requires token exchange "
                "with provider API. This is a stub response."
            ),
        }
