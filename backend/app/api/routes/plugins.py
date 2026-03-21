"""Plugin Marketplace routes — registration, enable/disable, execution."""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class PluginRegister(BaseModel):
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    entry_point: str = ""
    capabilities: list[str] = Field(default_factory=list)


class PluginExecute(BaseModel):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_plugins: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register")
async def register_plugin(body: PluginRegister) -> dict[str, Any]:
    """Register a new plugin."""
    pid = str(uuid.uuid4())
    plugin = {
        "id": pid,
        "name": body.name,
        "version": body.version,
        "description": body.description,
        "author": body.author,
        "entry_point": body.entry_point,
        "capabilities": body.capabilities,
        "enabled": False,
        "installed_at": time.time(),
    }
    _plugins[pid] = plugin
    return plugin


@router.get("/")
async def list_plugins() -> list[dict]:
    """List all registered plugins."""
    return list(_plugins.values())


@router.get("/{plugin_id}")
async def get_plugin(plugin_id: str) -> dict:
    """Get plugin details."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    return _plugins[plugin_id]


@router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str) -> dict[str, Any]:
    """Enable a plugin."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    _plugins[plugin_id]["enabled"] = True
    return {"plugin_id": plugin_id, "enabled": True}


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str) -> dict[str, Any]:
    """Disable a plugin."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    _plugins[plugin_id]["enabled"] = False
    return {"plugin_id": plugin_id, "enabled": False}


@router.post("/{plugin_id}/execute")
async def execute_plugin(plugin_id: str, body: PluginExecute) -> dict[str, Any]:
    """Execute a plugin action."""
    if plugin_id not in _plugins:
        raise HTTPException(status_code=404, detail="Plugin not found")
    if not _plugins[plugin_id]["enabled"]:
        raise HTTPException(status_code=400, detail="Plugin is not enabled")
    return {
        "plugin_id": plugin_id,
        "action": body.action,
        "status": "executed",
        "result": {"message": f"Action '{body.action}' executed successfully"},
    }


@router.get("/marketplace/featured")
async def marketplace_featured() -> list[dict]:
    """Get featured plugins from the marketplace."""
    return [
        {"name": "Auto-Label", "description": "Automatic image labeling", "downloads": 1520},
        {"name": "Video Summarizer", "description": "AI video summarization", "downloads": 980},
        {"name": "Data Augmentor", "description": "Smart data augmentation", "downloads": 2100},
    ]


# ---------------------------------------------------------------------------
# Extended marketplace plugin detail mock data
# ---------------------------------------------------------------------------

_MARKETPLACE_DETAIL: dict[str, dict[str, object]] = {
    "csv-exporter": {
        "name": "CSV Exporter",
        "category": "integration",
        "description": "Export any data as CSV",
        "version": "1.2.0",
        "author": "VAF Team",
        "install_count": 342,
        "avg_rating": 4.2,
        "icon": "integration",
        "full_description": (
            "CSV Exporter is a powerful integration plugin that lets you export any dataset, "
            "query result, or pipeline output as a well-formatted CSV file. It supports custom "
            "delimiters, encoding options, and streaming exports for large datasets.\n\n"
            "Whether you need to share data with stakeholders, import into spreadsheets, or "
            "create training data snapshots, CSV Exporter handles it seamlessly with minimal configuration."
        ),
        "features": [
            "Export datasets, query results, and pipeline outputs",
            "Custom delimiters (comma, tab, pipe, semicolon)",
            "UTF-8, Latin-1, and ASCII encoding support",
            "Streaming export for datasets over 1M rows",
            "Scheduled exports via cron expressions",
            "Automatic column type detection and formatting",
        ],
        "requirements": [
            "VAF Platform v2.0 or later",
            "At least one data source configured",
            "Write access to the target export directory",
        ],
        "compatibility": ["VAF Core 2.x", "Python 3.10+", "Linux", "macOS", "Windows"],
        "license": "MIT",
        "screenshots": [
            "/screenshots/csv-exporter-config.png",
            "/screenshots/csv-exporter-preview.png",
            "/screenshots/csv-exporter-output.png",
        ],
        "reviews": [
            {
                "id": "r1",
                "user": "Alice Chen",
                "avatar": "AC",
                "rating": 5,
                "date": "2026-03-10",
                "comment": "Works flawlessly with our million-row datasets. Streaming export is a game changer.",
                "helpful": 12,
            },
            {
                "id": "r2",
                "user": "Bob Martinez",
                "avatar": "BM",
                "rating": 4,
                "date": "2026-02-28",
                "comment": "Great plugin, just wish it had Parquet export too. CSV works well for our use case though.",
                "helpful": 5,
            },
            {
                "id": "r3",
                "user": "Carol Nguyen",
                "avatar": "CN",
                "rating": 4,
                "date": "2026-02-15",
                "comment": "Reliable and easy to configure. Scheduled exports save us a lot of manual work.",
                "helpful": 3,
            },
        ],
        "rating_breakdown": [
            {"stars": 5, "count": 156, "percentage": 46},
            {"stars": 4, "count": 112, "percentage": 33},
            {"stars": 3, "count": 48, "percentage": 14},
            {"stars": 2, "count": 18, "percentage": 5},
            {"stars": 1, "count": 8, "percentage": 2},
        ],
        "total_reviews": 342,
        "changelog": [
            {
                "version": "1.2.0",
                "date": "2026-03-01",
                "changes": [
                    "Added streaming export for large datasets (1M+ rows)",
                    "New scheduled export feature with cron support",
                    "Improved memory efficiency by 40%",
                ],
                "type": "minor",
            },
            {
                "version": "1.1.0",
                "date": "2026-01-15",
                "changes": [
                    "Added custom delimiter support",
                    "Added Latin-1 and ASCII encoding options",
                    "Fixed header row duplication bug",
                ],
                "type": "minor",
            },
            {
                "version": "1.0.0",
                "date": "2025-11-01",
                "changes": [
                    "Initial release with basic CSV export",
                    "UTF-8 encoding support",
                    "Column type auto-detection",
                ],
                "type": "major",
            },
        ],
    },
    "slack-notifier": {
        "name": "Slack Notifier",
        "category": "integration",
        "description": "Send alerts to Slack",
        "version": "1.3.1",
        "author": "VAF Team",
        "install_count": 510,
        "avg_rating": 4.5,
        "icon": "integration",
        "full_description": (
            "Slack Notifier integrates your VAF workflows with Slack, delivering real-time "
            "alerts, pipeline status updates, and anomaly notifications directly to your channels.\n\n"
            "Configure channel routing rules, message templates, and escalation policies to keep "
            "your team informed without alert fatigue."
        ),
        "features": [
            "Real-time pipeline alerts and status updates",
            "Channel routing by severity and category",
            "Rich message templates with Slack Block Kit",
            "Threaded replies for related alerts",
            "Mention users and groups on critical alerts",
            "Configurable rate limiting to prevent spam",
        ],
        "requirements": [
            "Slack workspace with bot token",
            "VAF Platform v2.0 or later",
            "Network access to Slack API",
        ],
        "compatibility": ["VAF Core 2.x", "Slack API v2", "Python 3.10+"],
        "license": "MIT",
        "screenshots": [
            "/screenshots/slack-notifier-config.png",
            "/screenshots/slack-notifier-message.png",
            "/screenshots/slack-notifier-routing.png",
        ],
        "reviews": [
            {
                "id": "r1",
                "user": "Dave Wilson",
                "avatar": "DW",
                "rating": 5,
                "date": "2026-03-12",
                "comment": "Essential plugin. Channel routing saves us from alert noise.",
                "helpful": 18,
            },
            {
                "id": "r2",
                "user": "Eve Patel",
                "avatar": "EP",
                "rating": 4,
                "date": "2026-03-01",
                "comment": "Solid integration. Would love to see Teams support in the future.",
                "helpful": 7,
            },
        ],
        "rating_breakdown": [
            {"stars": 5, "count": 280, "percentage": 55},
            {"stars": 4, "count": 153, "percentage": 30},
            {"stars": 3, "count": 51, "percentage": 10},
            {"stars": 2, "count": 18, "percentage": 3},
            {"stars": 1, "count": 8, "percentage": 2},
        ],
        "total_reviews": 510,
        "changelog": [
            {
                "version": "1.3.1",
                "date": "2026-03-05",
                "changes": ["Fixed rate limiter edge case", "Improved error messages"],
                "type": "patch",
            },
            {
                "version": "1.3.0",
                "date": "2026-02-10",
                "changes": [
                    "Added Block Kit message templates",
                    "Channel routing rules engine",
                    "Rate limiting configuration",
                ],
                "type": "minor",
            },
            {
                "version": "1.0.0",
                "date": "2025-10-01",
                "changes": ["Initial release with basic Slack notifications"],
                "type": "major",
            },
        ],
    },
    "yolo-detector": {
        "name": "YOLO Detector",
        "category": "vision",
        "description": "Object detection with YOLOv8",
        "version": "2.1.0",
        "author": "VAF Team",
        "install_count": 876,
        "avg_rating": 4.8,
        "icon": "vision",
        "full_description": (
            "YOLO Detector brings state-of-the-art object detection to your VAF pipelines using "
            "YOLOv8. Detect, classify, and track objects in images and video streams with "
            "production-grade accuracy and speed.\n\n"
            "Supports custom model weights, configurable confidence thresholds, and multi-GPU "
            "inference for high-throughput scenarios. Integrates seamlessly with VAF's vision "
            "pipeline for end-to-end object detection workflows."
        ),
        "features": [
            "YOLOv8 nano, small, medium, large, and xlarge models",
            "Real-time video stream detection",
            "Custom model weight loading",
            "Configurable confidence and IoU thresholds",
            "Multi-GPU inference support",
            "Bounding box, segmentation mask, and keypoint outputs",
            "Export detections as JSON, COCO, or Pascal VOC format",
        ],
        "requirements": [
            "VAF Platform v2.0 or later",
            "CUDA 11.8+ for GPU acceleration (optional)",
            "At least 4GB GPU VRAM for medium models",
            "Python 3.10+ with ultralytics package",
        ],
        "compatibility": ["VAF Core 2.x", "CUDA 11.8+", "Python 3.10+", "Linux", "macOS"],
        "license": "Apache-2.0",
        "screenshots": [
            "/screenshots/yolo-detection-preview.png",
            "/screenshots/yolo-config-panel.png",
            "/screenshots/yolo-batch-results.png",
        ],
        "reviews": [
            {
                "id": "r1",
                "user": "Frank Lee",
                "avatar": "FL",
                "rating": 5,
                "date": "2026-03-15",
                "comment": "Best detection plugin available. Multi-GPU support is incredibly well done.",
                "helpful": 24,
            },
            {
                "id": "r2",
                "user": "Grace Kim",
                "avatar": "GK",
                "rating": 5,
                "date": "2026-03-08",
                "comment": "Switching from our custom YOLO wrapper to this saved us weeks of maintenance.",
                "helpful": 15,
            },
            {
                "id": "r3",
                "user": "Henry Zhang",
                "avatar": "HZ",
                "rating": 4,
                "date": "2026-02-20",
                "comment": "Works great. Would appreciate YOLOv9 support when it stabilizes.",
                "helpful": 8,
            },
        ],
        "rating_breakdown": [
            {"stars": 5, "count": 612, "percentage": 70},
            {"stars": 4, "count": 175, "percentage": 20},
            {"stars": 3, "count": 53, "percentage": 6},
            {"stars": 2, "count": 26, "percentage": 3},
            {"stars": 1, "count": 10, "percentage": 1},
        ],
        "total_reviews": 876,
        "changelog": [
            {
                "version": "2.1.0",
                "date": "2026-03-01",
                "changes": [
                    "Added keypoint detection output mode",
                    "Multi-GPU load balancing improvements",
                    "Pascal VOC export format",
                ],
                "type": "minor",
            },
            {
                "version": "2.0.0",
                "date": "2026-01-01",
                "changes": [
                    "Upgraded to YOLOv8 engine",
                    "Added segmentation mask output",
                    "Breaking: new configuration schema",
                ],
                "type": "major",
            },
            {
                "version": "1.0.0",
                "date": "2025-08-01",
                "changes": ["Initial release with YOLOv5 support"],
                "type": "major",
            },
        ],
    },
    "whisper-transcriber": {
        "name": "Whisper Transcriber",
        "category": "audio",
        "description": "Speech-to-text with Whisper",
        "version": "1.4.0",
        "author": "VAF Team",
        "install_count": 654,
        "avg_rating": 4.7,
        "icon": "audio",
        "full_description": (
            "Whisper Transcriber leverages OpenAI's Whisper model for accurate speech-to-text "
            "transcription across 99+ languages. Process audio files, live streams, and batch "
            "jobs with configurable model sizes.\n\n"
            "Includes word-level timestamps, speaker diarization, and automatic language detection. "
            "Perfect for meeting transcription, content indexing, and accessibility workflows."
        ),
        "features": [
            "99+ language support with auto-detection",
            "Tiny, base, small, medium, and large model sizes",
            "Word-level timestamp alignment",
            "Speaker diarization (who said what)",
            "Batch processing with job queue",
            "SRT, VTT, and plain text output formats",
            "Live stream transcription (experimental)",
        ],
        "requirements": [
            "VAF Platform v2.0 or later",
            "CUDA 11.8+ for GPU acceleration (recommended)",
            "At least 2GB GPU VRAM for small model",
            "FFmpeg installed for audio preprocessing",
        ],
        "compatibility": ["VAF Core 2.x", "CUDA 11.8+", "FFmpeg 5+", "Python 3.10+"],
        "license": "MIT",
        "screenshots": [
            "/screenshots/whisper-transcription.png",
            "/screenshots/whisper-diarization.png",
            "/screenshots/whisper-batch-queue.png",
        ],
        "reviews": [
            {
                "id": "r1",
                "user": "Irene Costa",
                "avatar": "IC",
                "rating": 5,
                "date": "2026-03-18",
                "comment": "Transcription quality is outstanding. Speaker diarization works surprisingly well.",
                "helpful": 20,
            },
            {
                "id": "r2",
                "user": "Jack Murphy",
                "avatar": "JM",
                "rating": 4,
                "date": "2026-03-05",
                "comment": "Great for batch processing. Live stream mode is still a bit rough.",
                "helpful": 9,
            },
        ],
        "rating_breakdown": [
            {"stars": 5, "count": 392, "percentage": 60},
            {"stars": 4, "count": 170, "percentage": 26},
            {"stars": 3, "count": 59, "percentage": 9},
            {"stars": 2, "count": 20, "percentage": 3},
            {"stars": 1, "count": 13, "percentage": 2},
        ],
        "total_reviews": 654,
        "changelog": [
            {
                "version": "1.4.0",
                "date": "2026-03-10",
                "changes": [
                    "Added speaker diarization",
                    "Live stream transcription (experimental)",
                    "Improved word-level timestamp accuracy",
                ],
                "type": "minor",
            },
            {
                "version": "1.3.0",
                "date": "2026-01-20",
                "changes": ["SRT and VTT export formats", "Batch job queue with priority"],
                "type": "minor",
            },
            {
                "version": "1.0.0",
                "date": "2025-09-01",
                "changes": ["Initial release with Whisper small model"],
                "type": "major",
            },
        ],
    },
    "image-watermarker": {
        "name": "Image Watermarker",
        "category": "transform",
        "description": "Add watermarks to images",
        "version": "1.1.0",
        "author": "VAF Team",
        "install_count": 128,
        "avg_rating": 3.9,
        "icon": "transform",
        "full_description": (
            "Image Watermarker applies text or image-based watermarks to your visual assets. "
            "Supports batch processing with customizable position, opacity, and scaling.\n\n"
            "Protect your intellectual property and brand your outputs before distribution."
        ),
        "features": [
            "Text and image watermarks",
            "Batch processing of image directories",
            "Configurable position, opacity, and scale",
            "Support for PNG, JPEG, WebP, and TIFF",
            "Template-based watermark presets",
        ],
        "requirements": ["VAF Platform v2.0 or later", "Pillow or OpenCV installed"],
        "compatibility": ["VAF Core 2.x", "Python 3.10+", "Linux", "macOS", "Windows"],
        "license": "MIT",
        "screenshots": [
            "/screenshots/watermarker-config.png",
            "/screenshots/watermarker-preview.png",
            "/screenshots/watermarker-batch.png",
        ],
        "reviews": [
            {
                "id": "r1",
                "user": "Karen O'Brien",
                "avatar": "KO",
                "rating": 4,
                "date": "2026-02-25",
                "comment": "Simple and effective. Does exactly what it says.",
                "helpful": 4,
            },
        ],
        "rating_breakdown": [
            {"stars": 5, "count": 38, "percentage": 30},
            {"stars": 4, "count": 45, "percentage": 35},
            {"stars": 3, "count": 28, "percentage": 22},
            {"stars": 2, "count": 12, "percentage": 9},
            {"stars": 1, "count": 5, "percentage": 4},
        ],
        "total_reviews": 128,
        "changelog": [
            {
                "version": "1.1.0",
                "date": "2026-02-01",
                "changes": ["Added image-based watermarks", "Template presets", "WebP support"],
                "type": "minor",
            },
            {
                "version": "1.0.0",
                "date": "2025-10-15",
                "changes": ["Initial release with text watermarks"],
                "type": "major",
            },
        ],
    },
    "audio-normalizer": {
        "name": "Audio Normalizer",
        "category": "transform",
        "description": "Batch normalize audio files",
        "version": "1.0.2",
        "author": "VAF Team",
        "install_count": 95,
        "avg_rating": 4.0,
        "icon": "transform",
        "full_description": (
            "Audio Normalizer standardizes audio levels across files using peak and LUFS "
            "normalization. Ideal for preparing training data and ensuring consistent volume.\n\n"
            "Process entire directories in batch mode with configurable target levels."
        ),
        "features": [
            "Peak and LUFS normalization modes",
            "Batch directory processing",
            "Configurable target levels (-14 to -23 LUFS)",
            "WAV, FLAC, MP3, and OGG support",
            "Dry-run preview mode",
        ],
        "requirements": ["VAF Platform v2.0 or later", "FFmpeg installed"],
        "compatibility": ["VAF Core 2.x", "FFmpeg 5+", "Python 3.10+"],
        "license": "MIT",
        "screenshots": [
            "/screenshots/normalizer-config.png",
            "/screenshots/normalizer-waveform.png",
            "/screenshots/normalizer-batch.png",
        ],
        "reviews": [
            {
                "id": "r1",
                "user": "Liam Anderson",
                "avatar": "LA",
                "rating": 4,
                "date": "2026-03-02",
                "comment": "Works well for our training data prep pipeline.",
                "helpful": 6,
            },
        ],
        "rating_breakdown": [
            {"stars": 5, "count": 28, "percentage": 29},
            {"stars": 4, "count": 35, "percentage": 37},
            {"stars": 3, "count": 20, "percentage": 21},
            {"stars": 2, "count": 8, "percentage": 9},
            {"stars": 1, "count": 4, "percentage": 4},
        ],
        "total_reviews": 95,
        "changelog": [
            {
                "version": "1.0.2",
                "date": "2026-02-15",
                "changes": ["Fixed OGG processing crash", "Improved batch progress reporting"],
                "type": "patch",
            },
            {
                "version": "1.0.0",
                "date": "2025-11-01",
                "changes": ["Initial release with peak and LUFS normalization"],
                "type": "major",
            },
        ],
    },
    "sentiment-analyzer": {
        "name": "Sentiment Analyzer",
        "category": "analytics",
        "description": "Text sentiment analysis",
        "version": "1.1.0",
        "author": "VAF Team",
        "install_count": 231,
        "avg_rating": 4.1,
        "icon": "analytics",
        "full_description": (
            "Sentiment Analyzer processes text data to determine emotional tone — positive, "
            "negative, or neutral — with confidence scores. Uses transformer-based models for "
            "high accuracy across multiple languages.\n\n"
            "Useful for analyzing customer feedback, social media monitoring, and content moderation."
        ),
        "features": [
            "Positive, negative, neutral classification",
            "Confidence scores per class",
            "Multi-language support (en, es, fr, de, zh, ja)",
            "Batch text processing",
            "Aspect-based sentiment extraction",
            "CSV and JSON output formats",
        ],
        "requirements": ["VAF Platform v2.0 or later", "At least 2GB RAM for model loading"],
        "compatibility": ["VAF Core 2.x", "Python 3.10+", "Linux", "macOS", "Windows"],
        "license": "Apache-2.0",
        "screenshots": [
            "/screenshots/sentiment-dashboard.png",
            "/screenshots/sentiment-batch.png",
            "/screenshots/sentiment-aspect.png",
        ],
        "reviews": [
            {
                "id": "r1",
                "user": "Mia Thompson",
                "avatar": "MT",
                "rating": 4,
                "date": "2026-03-10",
                "comment": "Accurate and fast. Aspect-based extraction is a nice touch.",
                "helpful": 8,
            },
        ],
        "rating_breakdown": [
            {"stars": 5, "count": 69, "percentage": 30},
            {"stars": 4, "count": 92, "percentage": 40},
            {"stars": 3, "count": 46, "percentage": 20},
            {"stars": 2, "count": 16, "percentage": 7},
            {"stars": 1, "count": 8, "percentage": 3},
        ],
        "total_reviews": 231,
        "changelog": [
            {
                "version": "1.1.0",
                "date": "2026-02-01",
                "changes": [
                    "Added aspect-based sentiment extraction",
                    "Multi-language support (6 languages)",
                    "Performance improvements",
                ],
                "type": "minor",
            },
            {
                "version": "1.0.0",
                "date": "2025-10-01",
                "changes": ["Initial release with English sentiment analysis"],
                "type": "major",
            },
        ],
    },
    "report-generator": {
        "name": "Report Generator",
        "category": "analytics",
        "description": "Auto-generate PDF reports",
        "version": "1.2.0",
        "author": "VAF Team",
        "install_count": 189,
        "avg_rating": 3.8,
        "icon": "analytics",
        "full_description": (
            "Report Generator creates polished PDF reports from your pipeline outputs, metrics, "
            "and analytics data. Choose from built-in templates or design custom layouts.\n\n"
            "Schedule daily, weekly, or monthly reports and distribute them via email or Slack."
        ),
        "features": [
            "Built-in report templates (summary, detailed, executive)",
            "Custom layout designer",
            "Charts, tables, and image embedding",
            "Scheduled report generation",
            "Email and Slack distribution",
            "PDF and HTML output formats",
        ],
        "requirements": [
            "VAF Platform v2.0 or later",
            "wkhtmltopdf or WeasyPrint for PDF rendering",
        ],
        "compatibility": ["VAF Core 2.x", "Python 3.10+", "Linux", "macOS"],
        "license": "MIT",
        "screenshots": [
            "/screenshots/report-template.png",
            "/screenshots/report-preview.png",
            "/screenshots/report-schedule.png",
        ],
        "reviews": [
            {
                "id": "r1",
                "user": "Noah Baker",
                "avatar": "NB",
                "rating": 4,
                "date": "2026-02-28",
                "comment": "Templates are solid. Custom layout could be more intuitive.",
                "helpful": 5,
            },
        ],
        "rating_breakdown": [
            {"stars": 5, "count": 42, "percentage": 22},
            {"stars": 4, "count": 72, "percentage": 38},
            {"stars": 3, "count": 49, "percentage": 26},
            {"stars": 2, "count": 17, "percentage": 9},
            {"stars": 1, "count": 9, "percentage": 5},
        ],
        "total_reviews": 189,
        "changelog": [
            {
                "version": "1.2.0",
                "date": "2026-02-15",
                "changes": [
                    "Custom layout designer",
                    "HTML output format",
                    "Email distribution integration",
                ],
                "type": "minor",
            },
            {
                "version": "1.0.0",
                "date": "2025-10-01",
                "changes": ["Initial release with built-in templates and PDF output"],
                "type": "major",
            },
        ],
    },
}


@router.get("/marketplace/plugins/{plugin_id}")
async def marketplace_plugin_detail(plugin_id: str) -> dict[str, object]:
    """Get extended detail for a marketplace plugin by slug."""
    if plugin_id not in _MARKETPLACE_DETAIL:
        raise HTTPException(status_code=404, detail=f"Marketplace plugin '{plugin_id}' not found")
    return _MARKETPLACE_DETAIL[plugin_id]
