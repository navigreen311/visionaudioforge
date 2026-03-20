"""Retail Analytics vertical starter pack."""

from __future__ import annotations

from typing import Any

from app.services.verticals.base import VerticalPack


class RetailVerticalPack(VerticalPack):
    """Pre-built pipelines and alerts for retail analytics deployments.

    Covers foot-traffic counting, heatmap analysis, shelf monitoring,
    checkout-queue management, and loss-prevention workflows.
    """

    def info(self) -> dict[str, Any]:
        return {
            "name": "Retail Analytics",
            "slug": "retail",
            "icon": "shopping-cart",
            "description": (
                "Customer counting, heat-map analytics, shelf monitoring, "
                "queue management, and loss-prevention for retail environments."
            ),
            "category": "Retail",
        }

    # ------------------------------------------------------------------
    # Pipelines
    # ------------------------------------------------------------------

    def pipelines(self) -> dict[str, dict[str, Any]]:
        return {
            "customer_counting": {
                "name": "Customer Counting",
                "description": "Detect persons in video, count them, and produce an hourly traffic chart.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 30}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.45}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.4}},
                    {"id": "log_1", "type": "log", "params": {"label": "customer_count"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "hourly_traffic.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "log_1", "from_port": "output", "to_port": "input"},
                    {"from": "log_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "heat_map_analysis": {
                "name": "Heat Map Analysis",
                "description": "Track customer movement and generate a spatial heatmap overlay.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 60}},
                    {"id": "flow_1", "type": "optical_flow", "params": {"method": "farneback"}},
                    {"id": "normalize_1", "type": "normalize", "params": {"method": "min_max"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "heatmap.png", "format": "png"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "flow_1", "from_port": "output", "to_port": "input"},
                    {"from": "flow_1", "to": "normalize_1", "from_port": "output", "to_port": "input"},
                    {"from": "normalize_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "shelf_monitoring": {
                "name": "Shelf Monitoring",
                "description": "Detect empty shelves via object detection and trigger restock alerts.",
                "nodes": [
                    {"id": "input_1", "type": "input_image", "params": {"path": ""}},
                    {"id": "normalize_1", "type": "normalize", "params": {"method": "min_max"}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.5}},
                    {"id": "cond_1", "type": "conditional", "params": {"condition": "empty_shelf"}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "Empty shelf detected — restock needed", "severity": "warning"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "normalize_1", "from_port": "output", "to_port": "input"},
                    {"from": "normalize_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "cond_1", "from_port": "output", "to_port": "input"},
                    {"from": "cond_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "checkout_queue": {
                "name": "Checkout Queue Monitor",
                "description": "Count persons in checkout zone and alert when queue exceeds 5.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 15}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.45}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 5}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "Checkout queue exceeds threshold", "severity": "warning"}},
                    {"id": "save_1", "type": "save_asset", "params": {"filename": "queue_count.json", "format": "json"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                    {"from": "alert_1", "to": "save_1", "from_port": "output", "to_port": "input"},
                ],
            },
            "loss_prevention": {
                "name": "Loss Prevention",
                "description": "Detect suspicious behaviour patterns via motion analysis and object detection.",
                "nodes": [
                    {"id": "input_1", "type": "input_video", "params": {"path": "", "max_frames": 30}},
                    {"id": "diff_1", "type": "frame_diff", "params": {}},
                    {"id": "detect_1", "type": "detect_objects", "params": {"confidence": 0.5}},
                    {"id": "flow_1", "type": "optical_flow", "params": {"method": "farneback"}},
                    {"id": "filter_1", "type": "filter", "params": {"condition": "threshold", "value": 0.6}},
                    {"id": "alert_1", "type": "alert", "params": {"message": "Suspicious activity detected", "severity": "critical"}},
                ],
                "edges": [
                    {"from": "input_1", "to": "diff_1", "from_port": "output", "to_port": "input"},
                    {"from": "diff_1", "to": "detect_1", "from_port": "output", "to_port": "input"},
                    {"from": "detect_1", "to": "flow_1", "from_port": "output", "to_port": "input"},
                    {"from": "flow_1", "to": "filter_1", "from_port": "output", "to_port": "input"},
                    {"from": "filter_1", "to": "alert_1", "from_port": "output", "to_port": "input"},
                ],
            },
        }

    # ------------------------------------------------------------------
    # Alert presets
    # ------------------------------------------------------------------

    def alert_presets(self) -> dict[str, dict[str, Any]]:
        return {
            "long_queue": {
                "name": "Long Checkout Queue",
                "severity": "warning",
                "conditions": {"queue_length": {">": 5}},
                "cooldown_seconds": 120,
            },
            "empty_shelf": {
                "name": "Empty Shelf",
                "severity": "medium",
                "conditions": {"shelf_occupancy": {"<": 0.2}},
                "cooldown_seconds": 300,
            },
            "after_hours_motion": {
                "name": "After-Hours Motion",
                "severity": "critical",
                "conditions": {"motion_detected": True, "business_hours": False},
                "cooldown_seconds": 30,
            },
            "shrinkage_alert": {
                "name": "Shrinkage Alert",
                "severity": "high",
                "conditions": {"suspicious_score": {">": 0.75}},
                "cooldown_seconds": 60,
            },
        }

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def dashboard_widgets(self) -> list[dict[str, Any]]:
        return [
            {"type": "chart", "title": "Foot Traffic", "metric": "hourly_customer_count"},
            {"type": "funnel", "title": "Conversion Funnel", "metric": "conversion_rate"},
            {"type": "heatmap", "title": "Dwell Time Heatmap", "metric": "dwell_time"},
            {"type": "table", "title": "Top Products", "metric": "top_product_interactions"},
        ]

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def reports(self) -> dict[str, dict[str, Any]]:
        return {
            "daily_store_analytics": {
                "name": "Daily Store Analytics",
                "schedule": "daily",
                "sections": ["foot_traffic", "conversion", "dwell_time", "queue_wait"],
            },
            "weekly_performance": {
                "name": "Weekly Performance",
                "schedule": "weekly",
                "sections": ["traffic_trend", "sales_correlation", "staff_efficiency"],
            },
            "loss_prevention_summary": {
                "name": "Loss Prevention Summary",
                "schedule": "weekly",
                "sections": ["incidents", "shrinkage_estimate", "high_risk_zones"],
            },
        }
