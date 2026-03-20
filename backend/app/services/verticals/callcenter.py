"""Call Center vertical starter pack."""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class CallCenterVerticalPack(VerticalPack):
    """Pre-built pipelines and alerts for call-center / contact-center deployments."""

    def info(self) -> dict[str, Any]:
        return {
            "name": "Call Center",
            "slug": "callcenter",
            "icon": "headphones",
            "description": "Call transcription, sentiment analysis, agent coaching, and SLA monitoring.",
            "category": "Customer Service",
        }

    def pipelines(self) -> dict[str, dict[str, Any]]:
        return {
            "call_transcription": {
                "name": "Call Transcription",
                "description": "Transcribe incoming calls and extract MFCC features for analysis.",
                "nodes": [
                    {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                    {"id": "mfcc_1", "type": "mfcc", "params": {"n_mfcc": 13}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "transcription.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "mfcc_1", "from_port": "output", "to_port": "input"},
                    {"from": "mfcc_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "sentiment_analysis": {
                "name": "Sentiment Analysis",
                "description": "Analyze call audio for sentiment and emotional tone.",
                "nodes": [
                    {"id": "input_1", "type": "input_audio", "params": {"path": ""}},
                    {"id": "mel_1", "type": "mel_spectrogram", "params": {"n_mels": 128}},
                    {"id": "mfcc_1", "type": "mfcc", "params": {"n_mfcc": 13}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "sentiment.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "mel_1", "from_port": "output", "to_port": "input"},
                    {"from": "mel_1", "to": "mfcc_1", "from_port": "output", "to_port": "input"},
                    {"from": "mfcc_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
        }

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        return {
            "negative_sentiment": {
                "name": "Negative Sentiment Detected",
                "severity": "warning",
                "conditions": {"sentiment_score": {"<": -0.5}},
                "cooldown_seconds": 60,
            },
            "long_hold_time": {
                "name": "Long Hold Time",
                "severity": "high",
                "conditions": {"hold_seconds": {">": 300}},
                "cooldown_seconds": 120,
            },
        }

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return [
            {"type": "chart", "title": "Call Volume", "metric": "call_count"},
            {"type": "stat", "title": "Avg Handle Time", "metric": "avg_handle_time"},
            {"type": "chart", "title": "Sentiment Trend", "metric": "sentiment_avg"},
        ]

    def reports(self) -> dict[str, dict[str, Any]]:
        return {
            "daily_call_summary": {"name": "Daily Call Summary", "schedule": "daily"},
            "agent_performance": {"name": "Agent Performance Report", "schedule": "weekly"},
        }
