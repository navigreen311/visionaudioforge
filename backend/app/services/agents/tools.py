"""Tool definitions and execution for the copilot agent."""

import json
from datetime import datetime, timezone

COPILOT_TOOLS: list[dict] = [
    {
        "name": "search_media",
        "description": "Search the media library using text, image, or audio queries",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "modality": {
                    "type": "string",
                    "enum": ["text", "image", "audio"],
                    "description": "Type of search modality",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "analyze_image",
        "description": "Analyze an image for objects, text, and visual properties",
        "input_schema": {
            "type": "object",
            "properties": {
                "image_path": {
                    "type": "string",
                    "description": "Path or ID of the image to analyze",
                },
            },
            "required": ["image_path"],
        },
    },
    {
        "name": "analyze_audio",
        "description": "Analyze audio for spectral features, duration, and characteristics",
        "input_schema": {
            "type": "object",
            "properties": {
                "audio_path": {
                    "type": "string",
                    "description": "Path or ID of the audio file to analyze",
                },
            },
            "required": ["audio_path"],
        },
    },
    {
        "name": "create_alert",
        "description": "Create a new alert in the system",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["info", "warning", "error", "critical"],
                    "description": "Alert severity level",
                },
                "message": {
                    "type": "string",
                    "description": "Alert message content",
                },
                "details": {
                    "type": "string",
                    "description": "Additional details or context",
                },
            },
            "required": ["severity", "message"],
        },
    },
    {
        "name": "query_events",
        "description": "Query recent events from the event log",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Filter by event type",
                },
                "hours_back": {
                    "type": "integer",
                    "description": "How many hours back to query (default 24)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of events to return (default 20)",
                },
            },
        },
    },
    {
        "name": "get_system_status",
        "description": "Get platform health and operational statistics",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return the result as a string.

    V1 implementation returns realistic mock data. Production would call
    the actual service layer.
    """
    now = datetime.now(timezone.utc).isoformat()

    if tool_name == "search_media":
        query = tool_input.get("query", "")
        modality = tool_input.get("modality", "text")
        return json.dumps({
            "results": [
                {
                    "id": "asset-001",
                    "name": f"match_for_{query.replace(' ', '_')}.jpg",
                    "type": modality,
                    "relevance_score": 0.92,
                    "created_at": now,
                },
                {
                    "id": "asset-002",
                    "name": f"related_{query.replace(' ', '_')}.png",
                    "type": modality,
                    "relevance_score": 0.85,
                    "created_at": now,
                },
            ],
            "total_count": 2,
            "query": query,
            "modality": modality,
        })

    elif tool_name == "analyze_image":
        image_path = tool_input.get("image_path", "unknown")
        return json.dumps({
            "image_path": image_path,
            "objects_detected": [
                {"label": "person", "confidence": 0.95, "bbox": [100, 50, 300, 400]},
                {"label": "vehicle", "confidence": 0.87, "bbox": [400, 200, 600, 350]},
            ],
            "text_detected": ["STOP", "License: ABC-1234"],
            "properties": {
                "width": 1920,
                "height": 1080,
                "format": "JPEG",
                "color_space": "RGB",
                "dominant_colors": ["#2B3A4E", "#8CA0B3", "#D4E0EC"],
            },
        })

    elif tool_name == "analyze_audio":
        audio_path = tool_input.get("audio_path", "unknown")
        return json.dumps({
            "audio_path": audio_path,
            "duration_seconds": 34.5,
            "sample_rate": 44100,
            "channels": 2,
            "spectral_features": {
                "spectral_centroid_mean": 2847.3,
                "spectral_bandwidth_mean": 1923.7,
                "zero_crossing_rate": 0.082,
            },
            "mfcc_summary": {
                "num_coefficients": 13,
                "mean_energy": -12.4,
            },
            "detected_events": ["speech", "background_noise"],
        })

    elif tool_name == "create_alert":
        severity = tool_input.get("severity", "info")
        message = tool_input.get("message", "")
        return json.dumps({
            "alert_id": "alert-new-001",
            "severity": severity,
            "message": message,
            "details": tool_input.get("details", ""),
            "created_at": now,
            "status": "active",
        })

    elif tool_name == "query_events":
        event_type = tool_input.get("event_type", "all")
        limit = tool_input.get("limit", 20)
        hours_back = tool_input.get("hours_back", 24)
        return json.dumps({
            "events": [
                {
                    "id": "evt-001",
                    "event_type": event_type if event_type != "all" else "media_upload",
                    "source": "api",
                    "description": "New media asset uploaded",
                    "created_at": now,
                },
                {
                    "id": "evt-002",
                    "event_type": event_type if event_type != "all" else "pipeline_complete",
                    "source": "celery",
                    "description": "Processing pipeline completed",
                    "created_at": now,
                },
            ],
            "total_count": 2,
            "hours_back": hours_back,
            "limit": limit,
        })

    elif tool_name == "get_system_status":
        return json.dumps({
            "status": "healthy",
            "uptime_hours": 72.5,
            "services": {
                "api": "running",
                "database": "running",
                "redis": "running",
                "celery": "running",
                "minio": "running",
            },
            "stats": {
                "total_assets": 1247,
                "active_pipelines": 3,
                "pending_alerts": 2,
                "active_agents": 1,
                "storage_used_gb": 42.8,
            },
            "checked_at": now,
        })

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
