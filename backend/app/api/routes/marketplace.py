"""Marketplace routes — featured plugins, browsing with sort/pagination."""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SortOption(str, Enum):
    most_installed = "most_installed"
    top_rated = "top_rated"
    newest = "newest"
    a_z = "a_z"
    z_a = "z_a"


class MarketplacePlugin(BaseModel):
    name: str
    category: str
    description: str
    version: str
    author: str
    install_count: int
    avg_rating: float
    featured: bool = False


class PaginatedPlugins(BaseModel):
    plugins: list[MarketplacePlugin]
    total: int
    page: int
    per_page: int
    total_pages: int


# ---------------------------------------------------------------------------
# In-memory seed data
# ---------------------------------------------------------------------------

_SEED_PLUGINS: list[MarketplacePlugin] = [
    MarketplacePlugin(name="YOLO Detector", category="vision", description="Real-time object detection powered by YOLOv8. Detect, classify, and track objects across video streams.", version="2.1.0", author="VAF Core", install_count=876, avg_rating=4.8, featured=True),
    MarketplacePlugin(name="Whisper Transcriber", category="audio", description="High-accuracy speech-to-text transcription with OpenAI Whisper. Supports 50+ languages out of the box.", version="1.3.0", author="VAF Core", install_count=654, avg_rating=4.7, featured=True),
    MarketplacePlugin(name="Slack Notifier", category="integration", description="Instant Slack alerts for pipeline events, anomalies, and custom triggers.", version="1.1.0", author="VAF Core", install_count=510, avg_rating=4.5, featured=True),
    MarketplacePlugin(name="CSV Exporter", category="integration", description="Export any data as CSV with configurable delimiters and encodings.", version="1.0.0", author="VAF Community", install_count=342, avg_rating=4.2),
    MarketplacePlugin(name="Sentiment Analyzer", category="analytics", description="Text sentiment analysis using transformer models.", version="1.2.0", author="VAF Community", install_count=231, avg_rating=4.1),
    MarketplacePlugin(name="Report Generator", category="analytics", description="Auto-generate PDF reports from pipeline results.", version="1.0.0", author="VAF Community", install_count=189, avg_rating=3.8),
    MarketplacePlugin(name="Image Watermarker", category="transform", description="Add watermarks to images with customizable position and opacity.", version="1.0.0", author="VAF Community", install_count=128, avg_rating=3.9),
    MarketplacePlugin(name="Audio Normalizer", category="transform", description="Batch normalize audio files with peak and RMS modes.", version="1.0.0", author="VAF Community", install_count=95, avg_rating=4.0),
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/featured", response_model=list[MarketplacePlugin])
async def get_featured() -> list[MarketplacePlugin]:
    """Return featured marketplace plugins."""
    return [p for p in _SEED_PLUGINS if p.featured]


@router.get("/plugins", response_model=PaginatedPlugins)
async def list_plugins(
    sort: SortOption = Query(SortOption.most_installed, description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(12, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category (omit or 'all' for everything)"),
    search: str | None = Query(None, description="Search by name or description"),
) -> PaginatedPlugins:
    """Browse marketplace plugins with sorting, filtering, and pagination."""
    results = list(_SEED_PLUGINS)

    # -- category filter
    if category and category != "all":
        results = [p for p in results if p.category == category]

    # -- search filter
    if search:
        q = search.lower()
        results = [
            p for p in results
            if q in p.name.lower() or q in p.description.lower()
        ]

    # -- sort
    if sort == SortOption.most_installed:
        results.sort(key=lambda p: p.install_count, reverse=True)
    elif sort == SortOption.top_rated:
        results.sort(key=lambda p: p.avg_rating, reverse=True)
    elif sort == SortOption.newest:
        results.sort(key=lambda p: p.version, reverse=True)
    elif sort == SortOption.a_z:
        results.sort(key=lambda p: p.name.lower())
    elif sort == SortOption.z_a:
        results.sort(key=lambda p: p.name.lower(), reverse=True)

    total = len(results)
    total_pages = max(1, (total + per_page - 1) // per_page)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = results[start:end]

    return PaginatedPlugins(
        plugins=page_items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )
