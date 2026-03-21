"""Settings — Storage & Data Retention API routes."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings/storage", tags=["settings-storage"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CategoryUsage(BaseModel):
    category: str
    size_gb: float
    percentage: float
    color: str


class LargestAsset(BaseModel):
    id: str
    filename: str
    type: str
    size_mb: float
    last_accessed: str


class RetentionPolicy(BaseModel):
    category: str
    retention: str
    auto_delete_gb: float | None = None


class StorageUsage(BaseModel):
    used_gb: float
    total_gb: float
    categories: list[CategoryUsage]
    largest_assets: list[LargestAsset]
    retention_policies: list[RetentionPolicy]


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_MOCK_STORAGE = StorageUsage(
    used_gb=2.4,
    total_gb=10.0,
    categories=[
        CategoryUsage(category="Images", size_gb=1.2, percentage=50.0, color="#3B82F6"),
        CategoryUsage(category="Audio", size_gb=0.792, percentage=33.0, color="#8B5CF6"),
        CategoryUsage(category="Video", size_gb=0.3, percentage=12.5, color="#14B8A6"),
        CategoryUsage(category="Other", size_gb=0.108, percentage=4.5, color="#6B7280"),
    ],
    largest_assets=[
        LargestAsset(id="ast_001", filename="warehouse_cam_01.mp4", type="Video", size_mb=185.4, last_accessed="2026-03-18"),
        LargestAsset(id="ast_002", filename="training_batch_v3.zip", type="Other", size_mb=142.7, last_accessed="2026-03-10"),
        LargestAsset(id="ast_003", filename="defect_dataset.tar.gz", type="Other", size_mb=98.3, last_accessed="2026-03-15"),
        LargestAsset(id="ast_004", filename="audio_samples_q1.wav", type="Audio", size_mb=87.6, last_accessed="2026-03-19"),
        LargestAsset(id="ast_005", filename="floor_plan_hires.png", type="Images", size_mb=76.2, last_accessed="2026-03-20"),
        LargestAsset(id="ast_006", filename="inspection_feed.mp4", type="Video", size_mb=64.8, last_accessed="2026-03-12"),
        LargestAsset(id="ast_007", filename="env_noise_baseline.wav", type="Audio", size_mb=54.1, last_accessed="2026-03-14"),
        LargestAsset(id="ast_008", filename="annotated_frames.zip", type="Other", size_mb=48.9, last_accessed="2026-03-17"),
        LargestAsset(id="ast_009", filename="product_catalog.jpg", type="Images", size_mb=32.5, last_accessed="2026-03-20"),
        LargestAsset(id="ast_010", filename="shift_summary.png", type="Images", size_mb=28.1, last_accessed="2026-03-19"),
    ],
    retention_policies=[
        RetentionPolicy(category="Images", retention="forever", auto_delete_gb=None),
        RetentionPolicy(category="Audio", retention="90d", auto_delete_gb=2.0),
        RetentionPolicy(category="Video", retention="30d", auto_delete_gb=1.0),
        RetentionPolicy(category="Other", retention="1yr", auto_delete_gb=None),
    ],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=StorageUsage)
async def get_storage_usage() -> StorageUsage:
    """Return current storage usage, largest assets, and retention policies."""
    return _MOCK_STORAGE
