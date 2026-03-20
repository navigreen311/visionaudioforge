"""Vertical pack installer — provision and remove vertical resources for a workspace."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.verticals import VERTICAL_PACKS


class VerticalInstaller:
    """Install / uninstall vertical starter packs into workspaces."""

    # In-memory registry of installed packs per workspace (swap for DB table in production).
    _installed: dict[UUID, dict[str, dict]] = {}

    # ------------------------------------------------------------------
    # Install
    # ------------------------------------------------------------------

    @classmethod
    async def install_pack(
        cls,
        db: AsyncSession,
        workspace_id: UUID,
        pack_name: str,
    ) -> dict[str, Any]:
        """Install a vertical pack into the given workspace.

        Creates pipeline templates, alert rules, applies dashboard config,
        and records installation metadata.
        """
        pack_cls = VERTICAL_PACKS.get(pack_name)
        if pack_cls is None:
            raise ValueError(f"Unknown vertical pack: {pack_name}")

        pipelines = pack_cls.get_pipeline_templates()
        alert_presets = pack_cls.get_alert_presets()
        dashboard = pack_cls.get_dashboard_config()
        model_configs = pack_cls.get_model_configs()
        report_templates = pack_cls.get_report_templates()

        # Persist installation record
        ws_packs = cls._installed.setdefault(workspace_id, {})
        ws_packs[pack_name] = {
            "info": pack_cls.PACK_INFO,
            "pipelines": pipelines,
            "alert_presets": alert_presets,
            "dashboard": dashboard,
            "model_configs": model_configs,
            "report_templates": report_templates,
        }

        return {
            "installed": True,
            "pipelines_created": len(pipelines),
            "rules_created": len(alert_presets),
            "configs_applied": len(model_configs) + 1,  # +1 for dashboard
        }

    # ------------------------------------------------------------------
    # Uninstall
    # ------------------------------------------------------------------

    @classmethod
    async def uninstall_pack(
        cls,
        db: AsyncSession,
        workspace_id: UUID,
        pack_name: str,
    ) -> dict[str, Any]:
        """Remove a previously installed vertical pack from a workspace."""
        ws_packs = cls._installed.get(workspace_id, {})
        if pack_name in ws_packs:
            del ws_packs[pack_name]
            return {"removed": True}
        return {"removed": False}

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @classmethod
    async def list_available_packs(cls) -> list[dict]:
        """Return metadata for every registered vertical pack."""
        return [
            {"pack_name": name, **pack_cls.PACK_INFO}
            for name, pack_cls in VERTICAL_PACKS.items()
        ]

    @classmethod
    async def list_installed_packs(
        cls,
        db: AsyncSession,
        workspace_id: UUID,
    ) -> list[dict]:
        """Return the list of packs currently installed for a workspace."""
        ws_packs = cls._installed.get(workspace_id, {})
        return [
            {"pack_name": name, **data["info"]}
            for name, data in ws_packs.items()
        ]

    @classmethod
    async def get_pack_info(cls, pack_name: str) -> dict[str, Any]:
        """Return full details for a vertical pack (without installing)."""
        pack_cls = VERTICAL_PACKS.get(pack_name)
        if pack_cls is None:
            raise ValueError(f"Unknown vertical pack: {pack_name}")
        return {
            "info": pack_cls.PACK_INFO,
            "pipelines": pack_cls.get_pipeline_templates(),
            "alert_presets": pack_cls.get_alert_presets(),
            "dashboard": pack_cls.get_dashboard_config(),
            "report_templates": pack_cls.get_report_templates(),
            "model_configs": pack_cls.get_model_configs(),
        }
