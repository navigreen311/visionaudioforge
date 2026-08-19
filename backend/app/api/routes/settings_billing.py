"""Settings Billing API - plan, usage meters, and billing history."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.config import settings
from app.core.deps import get_db, get_workspace_id
from app.models.asset import Asset
from app.models.model_registry import ModelRecord
from app.models.user import User
from app.models.workspace import Workspace

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PlanFeature(BaseModel):
    name: str
    free: str
    starter: str
    pro: str
    enterprise: str


class UsageMeter(BaseModel):
    label: str
    current: float
    limit: float
    unit: str
    color: str
    reset_date: str


class BillingHistoryItem(BaseModel):
    id: str
    date: str
    description: str
    amount: str
    status: str
    invoice_url: str | None = None


class BillingResponse(BaseModel):
    plan: str
    plan_label: str
    features: list[PlanFeature]
    usage: list[UsageMeter]
    history: list[BillingHistoryItem]


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_FEATURES: list[PlanFeature] = [
    PlanFeature(
        name="API Calls / month",
        free="1,000",
        starter="10,000",
        pro="100,000",
        enterprise="Unlimited",
    ),
    PlanFeature(
        name="Storage",
        free="1 GB",
        starter="10 GB",
        pro="100 GB",
        enterprise="Unlimited",
    ),
    PlanFeature(
        name="Live Streams",
        free="0",
        starter="2",
        pro="10",
        enterprise="Unlimited",
    ),
    PlanFeature(
        name="Team Members",
        free="1",
        starter="3",
        pro="10",
        enterprise="Unlimited",
    ),
    PlanFeature(
        name="Pipeline Runs / month",
        free="50",
        starter="500",
        pro="5,000",
        enterprise="Unlimited",
    ),
    PlanFeature(
        name="Priority Support",
        free="--",
        starter="Email",
        pro="Email + Chat",
        enterprise="Dedicated",
    ),
    PlanFeature(
        name="Custom Models",
        free="--",
        starter="1",
        pro="5",
        enterprise="Unlimited",
    ),
]

_USAGE: list[UsageMeter] = [
    UsageMeter(
        label="API Calls",
        current=1240,
        limit=10000,
        unit="calls",
        color="blue",
        reset_date="2026-04-01",
    ),
    UsageMeter(
        label="Storage",
        current=2.4,
        limit=10,
        unit="GB",
        color="purple",
        reset_date="2026-04-01",
    ),
    UsageMeter(
        label="Live Streams",
        current=0,
        limit=2,
        unit="streams",
        color="green",
        reset_date="2026-04-01",
    ),
    UsageMeter(
        label="Team Members",
        current=1,
        limit=3,
        unit="members",
        color="amber",
        reset_date="2026-04-01",
    ),
    UsageMeter(
        label="Pipeline Runs",
        current=56,
        limit=500,
        unit="runs",
        color="rose",
        reset_date="2026-04-01",
    ),
]

_HISTORY: list[BillingHistoryItem] = [
    BillingHistoryItem(
        id="inv_001",
        date="2026-03-01",
        description="Starter Plan - Monthly",
        amount="$29.00",
        status="paid",
        invoice_url="/invoices/inv_001.pdf",
    ),
    BillingHistoryItem(
        id="inv_002",
        date="2026-02-01",
        description="Starter Plan - Monthly",
        amount="$29.00",
        status="paid",
        invoice_url="/invoices/inv_002.pdf",
    ),
    BillingHistoryItem(
        id="inv_003",
        date="2026-01-01",
        description="Starter Plan - Monthly",
        amount="$29.00",
        status="paid",
        invoice_url="/invoices/inv_003.pdf",
    ),
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/billing", response_model=BillingResponse)
async def get_billing(
    session_workspace: UUID = Depends(get_workspace_id),
    db: AsyncSession = Depends(get_db),
) -> BillingResponse:
    """The workspace's plan and what it has actually consumed.

    This returned a fixed "starter" plan with invented usage meters and a
    fabricated payment history, so every workspace saw the same bill regardless
    of its plan or its usage.

    Plan and usage are now measured. History stays empty: no billing provider is
    connected, and inventing a payment record is the last thing this endpoint
    should do. The feature list is a static plan catalogue, which is legitimately
    static.
    """
    workspace = await db.get(Workspace, session_workspace)
    plan = getattr(workspace, "plan", None) or "free"
    plan_name = getattr(plan, "value", str(plan))

    async def _count(model) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(model)
            .where(model.workspace_id == session_workspace)
        )
        return int(result.scalar() or 0)

    stored_bytes = int(
        (
            await db.execute(
                select(func.coalesce(func.sum(Asset.size_bytes), 0)).where(
                    Asset.workspace_id == session_workspace
                )
            )
        ).scalar()
        or 0
    )
    stored_gb = round(stored_bytes / 1_000_000_000, 3)

    def _meter(label: str, current: float, limit: float, unit: str) -> UsageMeter:
        ratio = (current / limit) if limit else 0.0
        return UsageMeter(
            label=label,
            current=current,
            limit=limit,
            unit=unit,
            color="red" if ratio >= 0.9 else "amber" if ratio >= 0.7 else "green",
            # No billing cycle exists, so there is no reset date to report.
            reset_date="",
        )

    return BillingResponse(
        plan=plan_name,
        plan_label=plan_name.title(),
        features=_FEATURES,
        usage=[
            _meter("Assets", await _count(Asset), 0, "items"),
            _meter("Storage", stored_gb, float(settings.STORAGE_QUOTA_GB), "GB"),
            _meter("Models", await _count(ModelRecord), 0, "items"),
            _meter("Members", await _count(User), 0, "people"),
        ],
        history=[],
    )


