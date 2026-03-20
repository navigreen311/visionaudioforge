"""Embeddable widget service — generate embed snippets and validate tokens."""

from __future__ import annotations

import hashlib
import secrets
import time
from typing import Any


# ---------------------------------------------------------------------------
# Token store (production: DB / Redis)
# ---------------------------------------------------------------------------

_TOKEN_STORE: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# WidgetService
# ---------------------------------------------------------------------------

WIDGET_TYPES = [
    "live_feed",
    "alert_badge",
    "search_bar",
    "metric_card",
    "chart",
    "copilot_mini",
]


class WidgetService:
    """Generate embeddable widget snippets and validate embed tokens."""

    @staticmethod
    def get_widget_types() -> list[str]:
        return list(WIDGET_TYPES)

    @staticmethod
    def generate_embed_code(widget_type: str, config: dict) -> dict:
        if widget_type not in WIDGET_TYPES:
            raise ValueError(
                f"Unknown widget type '{widget_type}'. "
                f"Must be one of {WIDGET_TYPES}"
            )

        token = secrets.token_urlsafe(32)
        workspace_id = config.get("workspace_id", "default")
        permissions = config.get("permissions", ["read"])

        _TOKEN_STORE[token] = {
            "workspace_id": workspace_id,
            "widget_type": widget_type,
            "permissions": permissions,
            "created_at": time.time(),
        }

        width = config.get("width", 400)
        height = config.get("height", 300)

        base_url = "https://app.vaf.io"
        iframe_url = f"{base_url}/embed/{widget_type}?token={token}"
        script_url = f"{base_url}/embed/sdk.js"

        html = (
            f'<iframe src="{iframe_url}" '
            f'width="{width}" height="{height}" '
            f'frameborder="0" allowtransparency="true"></iframe>'
        )

        return {"html": html, "script_url": script_url, "iframe_url": iframe_url}

    @staticmethod
    async def validate_embed_token(token: str) -> dict:
        entry = _TOKEN_STORE.get(token)
        if not entry:
            return {
                "valid": False,
                "workspace_id": "",
                "widget_type": "",
                "permissions": [],
            }
        return {
            "valid": True,
            "workspace_id": entry["workspace_id"],
            "widget_type": entry["widget_type"],
            "permissions": entry["permissions"],
        }
