"""Policy engine for safety and privacy rule evaluation."""

from __future__ import annotations

import copy
from typing import Any


# Built-in policy definitions
BUILT_IN_POLICIES: dict[str, dict] = {
    "strict_pii": {
        "name": "strict_pii",
        "rules": [
            {"type": "restrict_export", "condition": "pii_detected", "action": "block"},
        ],
        "description": "Block export if any PII is detected.",
    },
    "face_privacy": {
        "name": "face_privacy",
        "rules": [
            {"type": "require_transform", "condition": "face_detected", "action": "blur_faces"},
        ],
        "description": "Blur all faces before export.",
    },
    "content_review": {
        "name": "content_review",
        "rules": [
            {"type": "require_approval", "condition": "risk_above_threshold", "action": "queue_review"},
        ],
        "description": "Queue for human review if risk > 0.5.",
    },
}

# In-memory consent store (user_id -> set of voice_owner_ids)
_consent_records: dict[str, set[str]] = {}


class PolicyEngine:
    """Evaluate content against configurable safety/privacy policies."""

    # ------------------------------------------------------------------
    # Policy CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def create_policy(name: str, rules: list[dict]) -> dict:
        """Create a new policy definition (returns the policy dict)."""
        return {
            "name": name,
            "rules": copy.deepcopy(rules),
        }

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def evaluate_policy(policy: dict, scan_result: dict) -> dict:
        """Evaluate a policy against a scan result.

        Returns ``{"allowed": bool, "violations": [...], "required_actions": [...]}``.
        """
        violations: list[str] = []
        required_actions: list[str] = []

        for rule in policy.get("rules", []):
            condition = rule.get("condition", "")
            action = rule.get("action", "")
            rule_type = rule.get("type", "")

            triggered = PolicyEngine._check_condition(condition, scan_result)
            if triggered:
                if rule_type == "restrict_export":
                    violations.append(f"Policy violation: {condition} — action: {action}")
                elif rule_type == "require_approval":
                    required_actions.append(f"Approval required: {condition} — action: {action}")
                elif rule_type == "require_transform":
                    required_actions.append(f"Transform required: {condition} — action: {action}")
                else:
                    violations.append(f"Rule triggered: {condition} — action: {action}")

        allowed = len(violations) == 0
        return {
            "allowed": allowed,
            "violations": violations,
            "required_actions": required_actions,
        }

    # ------------------------------------------------------------------
    # Convenience checks
    # ------------------------------------------------------------------

    @staticmethod
    def check_export_allowed(
        scan_result: dict, policy_name: str = "strict_pii"
    ) -> dict:
        """Check whether an asset export is allowed under a named policy.

        Returns ``{"allowed": bool, "reason": str}``.
        """
        policy = BUILT_IN_POLICIES.get(policy_name)
        if policy is None:
            return {"allowed": False, "reason": f"Unknown policy: {policy_name}"}

        result = PolicyEngine.evaluate_policy(policy, scan_result)
        if result["allowed"]:
            reason = "Export permitted — no policy violations."
        else:
            reason = "; ".join(result["violations"])
        return {"allowed": result["allowed"], "reason": reason}

    @staticmethod
    def check_voice_clone_consent(user_id: str, voice_owner_id: str) -> dict:
        """Check if explicit consent exists for voice cloning.

        Returns ``{"consent": bool, "note": str}``.
        """
        consents = _consent_records.get(voice_owner_id, set())
        if user_id in consents:
            return {"consent": True, "note": "Explicit consent on file."}
        return {
            "consent": False,
            "note": "No consent record found. Explicit consent from voice owner is required.",
        }

    @staticmethod
    def record_voice_consent(user_id: str, voice_owner_id: str) -> None:
        """Record voice-cloning consent (helper for tests and admin)."""
        _consent_records.setdefault(voice_owner_id, set()).add(user_id)

    # ------------------------------------------------------------------
    # Internal condition evaluator
    # ------------------------------------------------------------------

    @staticmethod
    def _check_condition(condition: str, scan_result: dict) -> bool:
        """Evaluate a condition string against a scan result."""
        if condition == "pii_detected":
            return len(scan_result.get("pii_found", [])) > 0

        if condition == "face_detected":
            return scan_result.get("faces_detected", 0) > 0

        if condition == "risk_above_threshold":
            return scan_result.get("risk_score", 0.0) > 0.5

        # Support "face_count > N" pattern
        if condition.startswith("face_count"):
            try:
                parts = condition.split(">")
                threshold = int(parts[1].strip())
                return scan_result.get("faces_detected", 0) > threshold
            except (IndexError, ValueError):
                return False

        return False
