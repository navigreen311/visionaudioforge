"""Media Production vertical starter pack."""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class MediaVerticalPack(VerticalPack):
    """Pre-built pipelines and alerts for media production deployments.

    Covers content review / moderation, automatic highlight extraction,
    podcast production, subtitle generation, and thumbnail generation.
    """

    def info(self) -> dict[str, Any]:
        return {
            "name": "Media Production",
            "slug": "media",
            "icon": "film",
            "description": (
                "Content moderation, auto-highlight extraction, podcast production, "
                "subtitle generation, and thumbnail creation for media teams."
            ),
            "category": "Media & Entertainment",
        }

    # ------------------------------------------------------------------
    # Pipelines
    # ------------------------------------------------------------------

    def pipelines(self) -> dict[str, dict[str, Any]]:
        return {
            "content_review": {
                "name": "Content Review",
                "description": "Upload media, run content-safety scan, quality check, and approve or reject.",
                "nodes": [
                    {"id": "input_1", "type": "input_image", "params": {"path": ""}},
                    {"id": "normalize_1", "type": "normalize", "params": {"method": "min_max"}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.4}},
                    {"id": "cond_1", "type": "conditional", "params": {"condition": "safe"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "review_result.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "normalize_1", "from_port": "output", "to_port": "input"},
                    {"from": "normalize_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "cond_1", "from_port": "output", "to_port": "input"},
                    {"from": "cond_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "auto_highlight": {
                "name": "Auto Highlight Extraction",
                "description": "Analyze video, detect scene changes, score segments, and extract highlights.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 120}},
                    {"id": "diff_1", "type": "frame_diff", "params": {}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.5}},
                    {"id": "log_1", "type": "log", "params": {"label": "highlight_score"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "highlights.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "diff_1", "from_port": "output", "to_port": "input"},
                    {"from": "diff_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "log_1", "from_port": "output", "to_port": "input"},
                    {"from": "log_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "podcast_production": {
                "name": "Podcast Production",
                "description": "Denoise audio, normalize levels, detect chapters, and export final audio.",
                "nodes": [
                    {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                    {"id": "augment_1", "type": "augment_audio", "params": {"augmentation": "noise", "intensity": -0.003}},
                    {"id": "stft_1", "type": "stft", "params": {"n_fft": 2048}},
                    {"id": "mfcc_1", "type": "mfcc", "params": {"n_mfcc": 13}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "podcast_final.npy", "format": "npy"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "augment_1", "from_port": "output", "to_port": "input"},
                    {"from": "augment_1", "to": "stft_1", "from_port": "output", "to_port": "input"},
                    {"from": "stft_1", "to": "mfcc_1", "from_port": "output", "to_port": "input"},
                    {"from": "mfcc_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "subtitle_generation": {
                "name": "Subtitle Generation",
                "description": "Extract audio from video, transcribe, and produce subtitle output.",
                "nodes": [
                    {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                    {"id": "mfcc_1", "type": "mfcc", "params": {"n_mfcc": 13}},
                    {"id": "mel_1", "type": "mel_spectrogram", "params": {"n_mels": 80}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "subtitles.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "mfcc_1", "from_port": "output", "to_port": "input"},
                    {"from": "mfcc_1", "to": "mel_1", "from_port": "output", "to_port": "input"},
                    {"from": "mel_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "thumbnail_generation": {
                "name": "Thumbnail Generation",
                "description": "Detect scene changes, select the best frame, auto-crop, and export as thumbnail.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 60}},
                    {"id": "diff_1", "type": "frame_diff", "params": {}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "top_k", "value": 1}},
                    {"id": "resize_1", "type": "resize", "params": {"width": 1280, "height": 720}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "thumbnail.png", "format": "png"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "diff_1", "from_port": "output", "to_port": "input"},
                    {"from": "diff_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "resize_1", "from_port": "output", "to_port": "input"},
                    {"from": "resize_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
        }

    # ------------------------------------------------------------------
    # Alert presets
    # ------------------------------------------------------------------

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        return {
            "content_flagged": {
                "name": "Content Flagged",
                "severity": "high",
                "conditions": {"safety_score": {"<": 0.3}},
                "cooldown_seconds": 0,
            },
            "processing_stalled": {
                "name": "Processing Stalled",
                "severity": "medium",
                "conditions": {"queue_wait_seconds": {">": 600}},
                "cooldown_seconds": 300,
            },
            "storage_threshold": {
                "name": "Storage Threshold Reached",
                "severity": "warning",
                "conditions": {"storage_usage_pct": {">": 90}},
                "cooldown_seconds": 3600,
            },
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return [
            {"type": "stat", "title": "Content Queue", "metric": "pending_review_count"},
            {"type": "chart", "title": "Approval Rate", "metric": "approval_rate_trend"},
            {"type": "stat", "title": "Avg Processing Time", "metric": "avg_processing_seconds"},
            {"type": "gauge", "title": "Storage Usage", "metric": "storage_usage_pct"},
        ]

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def reports(self) -> dict[str, dict[str, Any]]:
        return {
            "content_catalog": {
                "name": "Content Catalog",
                "schedule": "daily",
                "sections": ["new_uploads", "approved", "rejected", "pending"],
            },
            "production_metrics": {
                "name": "Production Metrics",
                "schedule": "weekly",
                "sections": ["processing_time", "throughput", "error_rate"],
            },
            "quality_report": {
                "name": "Quality Report",
                "schedule": "weekly",
                "sections": ["resolution_stats", "format_distribution", "flagged_content"],
            },
        }
