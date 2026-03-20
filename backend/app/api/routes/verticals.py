"""Vertical starter-pack routes — browse, install, uninstall, and generate reports."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.verticals.installer import VerticalInstaller
from app.services.verticals.report_templates import ReportTemplateService

router = APIRouter(prefix="/api/verticals", tags=["verticals"])


# ------------------------------------------------------------------
# Request / response helpers
# ------------------------------------------------------------------

class DailySummaryRequest(BaseModel):
    workspace_id: UUID
    date: str  # ISO-8601 date string


class IncidentReportRequest(BaseModel):
    workspace_id: UUID


# ------------------------------------------------------------------
# Pack browsing
# ------------------------------------------------------------------


@router.get("")
async def list_available_packs():
    """List all available vertical packs."""
    return await VerticalInstaller.list_available_packs()


@router.get("/installed")
async def list_installed_packs(
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
):
    """List packs installed in the given workspace."""
    return await VerticalInstaller.list_installed_packs(db, workspace_id)


@router.get("/{name}")
async def get_pack_details(name: str):
    """Return full details for a vertical pack."""
    try:
        return await VerticalInstaller.get_pack_info(name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ------------------------------------------------------------------
# Install / uninstall
# ------------------------------------------------------------------


@router.post("/{name}/install")
async def install_pack(
    name: str,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
):
    """Install a vertical pack into the workspace."""
    try:
        result = await VerticalInstaller.install_pack(db, workspace_id, name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result


@router.post("/{name}/uninstall")
async def uninstall_pack(
    name: str,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
):
    """Uninstall a vertical pack from the workspace."""
    result = await VerticalInstaller.uninstall_pack(db, workspace_id, name)
    if not result["removed"]:
        raise HTTPException(status_code=404, detail="Pack not installed in this workspace")
    return result


# ------------------------------------------------------------------
# Reports
# ------------------------------------------------------------------


@router.post("/reports/daily-summary")
async def daily_summary(
    body: DailySummaryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a daily security summary report."""
    return await ReportTemplateService.generate_daily_summary(
        db, body.workspace_id, body.date,
    )


@router.post("/reports/incident/{incident_id}")
async def incident_report(
    incident_id: str,
    workspace_id: UUID = Query(..., description="Workspace ID"),
    db: AsyncSession = Depends(get_db),
):
    """Generate a detailed incident report."""
    return await ReportTemplateService.generate_incident_report(db, incident_id)
