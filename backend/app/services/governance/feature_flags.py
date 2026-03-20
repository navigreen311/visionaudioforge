"""Feature flags: plan-gated feature access control."""

from typing import Any


FLAGS: dict[str, dict[str, Any]] = {
    "capture_rtsp": {"plans": ["pro", "enterprise"]},
    "pipeline_scheduling": {"plans": ["pro", "enterprise"]},
    "copilot": {"plans": ["pro", "enterprise"]},
    "advanced_analytics": {"plans": ["enterprise"]},
    "custom_models": {"plans": ["pro", "enterprise"]},
    "api_access": {"plans": ["pro", "enterprise"]},
    "sso": {"plans": ["enterprise"]},
    "white_label": {"plans": ["enterprise"]},
}


class FeatureFlagService:
    """Plan-gated feature flag management."""

    @staticmethod
    def is_enabled(flag_name: str, plan: str) -> bool:
        """Check if a feature flag is enabled for a plan."""
        flag = FLAGS.get(flag_name)
        if flag is None:
            return False
        return plan in flag["plans"]

    @staticmethod
    def get_enabled_features(plan: str) -> list[str]:
        """Return all enabled feature names for a plan."""
        return [
            name
            for name, config in FLAGS.items()
            if plan in config["plans"]
        ]

    @staticmethod
    def check_feature(flag_name: str, workspace_plan: str) -> dict[str, Any]:
        """Check a feature and suggest upgrade if not available."""
        flag = FLAGS.get(flag_name)
        if flag is None:
            return {"enabled": False, "upgrade_to": None}

        if workspace_plan in flag["plans"]:
            return {"enabled": True, "upgrade_to": None}

        # Suggest the cheapest plan that has this feature
        plan_order = ["free", "pro", "enterprise"]
        for p in plan_order:
            if p in flag["plans"]:
                return {"enabled": False, "upgrade_to": p}

        return {"enabled": False, "upgrade_to": None}
