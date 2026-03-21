"""Settings Billing API — plan, usage meters, and billing history."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

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
async def get_billing():
    """Return current plan, usage meters, and billing history.

    Returns mock data — will be wired to Stripe / billing service later.
    """
    return BillingResponse(
        plan="starter",
        plan_label="Starter",
        features=_FEATURES,
        usage=_USAGE,
        history=_HISTORY,
    )
