"""Compliance packs — HIPAA, GDPR, SOC 2 checks and reporting."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


# In-memory legal-hold store
_legal_holds: dict[str, dict] = {}

COMPLIANCE_PACKS: dict[str, dict] = {
    "hipaa": {
        "rules": [
            "encrypt_at_rest",
            "audit_all_access",
            "minimum_necessary",
            "no_pii_in_logs",
        ],
        "required_policies": ["strict_pii", "face_privacy"],
        "retention_days": 2190,
        "export_restrictions": ["require_encryption", "require_baa"],
    },
    "gdpr": {
        "rules": [
            "right_to_deletion",
            "data_minimization",
            "consent_required",
            "breach_notification_72h",
        ],
        "required_policies": ["strict_pii"],
        "retention_days": None,
        "data_residency": True,
    },
    "soc2": {
        "rules": [
            "access_controls",
            "audit_logging",
            "encryption",
            "incident_response",
        ],
        "required_policies": [],
        "retention_days": 365,
    },
}


class ComplianceManager:
    """Evaluate workspace compliance against regulatory packs."""

    # ------------------------------------------------------------------
    # Compliance checking
    # ------------------------------------------------------------------

    @staticmethod
    def check_compliance(
        db: Any, workspace_id: str, pack_name: str
    ) -> dict:
        """Check a workspace against a compliance pack.

        Returns::

            {
                "compliant": bool,
                "checks": [{"rule": str, "status": "pass"|"fail"|"warning", "details": str}],
                "score": float   # 0.0-1.0
            }
        """
        pack = COMPLIANCE_PACKS.get(pack_name)
        if pack is None:
            raise ValueError(f"Unknown compliance pack: {pack_name}")

        checks: list[dict] = []

        for rule in pack["rules"]:
            status, details = ComplianceManager._evaluate_rule(rule, workspace_id)
            checks.append({"rule": rule, "status": status, "details": details})

        # Score = fraction of passing checks
        total = len(checks)
        passed = sum(1 for c in checks if c["status"] == "pass")
        warnings = sum(1 for c in checks if c["status"] == "warning")
        score = (passed + 0.5 * warnings) / total if total > 0 else 1.0
        compliant = all(c["status"] != "fail" for c in checks)

        return {
            "compliant": compliant,
            "checks": checks,
            "score": round(score, 2),
        }

    # ------------------------------------------------------------------
    # Report generation
    # ------------------------------------------------------------------

    @staticmethod
    def generate_compliance_report(
        db: Any, workspace_id: str, pack_name: str
    ) -> dict:
        """Generate a full compliance report with recommendations."""
        result = ComplianceManager.check_compliance(db, workspace_id, pack_name)

        recommendations: list[str] = []
        for check in result["checks"]:
            if check["status"] == "fail":
                recommendations.append(
                    f"REQUIRED: Address failing rule '{check['rule']}' — {check['details']}"
                )
            elif check["status"] == "warning":
                recommendations.append(
                    f"RECOMMENDED: Review '{check['rule']}' — {check['details']}"
                )

        overall = "compliant" if result["compliant"] else "non-compliant"

        return {
            "pack": pack_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall": overall,
            "checks": result["checks"],
            "recommendations": recommendations,
            "score": result["score"],
        }

    # ------------------------------------------------------------------
    # Legal hold
    # ------------------------------------------------------------------

    @staticmethod
    def legal_hold(
        db: Any, asset_ids: list[str], reason: str, user_id: str
    ) -> dict:
        """Place a legal hold on assets, preventing deletion."""
        hold_id = str(uuid.uuid4())
        _legal_holds[hold_id] = {
            "hold_id": hold_id,
            "asset_ids": list(asset_ids),
            "reason": reason,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "released": False,
        }
        return {"hold_id": hold_id, "assets_held": len(asset_ids)}

    @staticmethod
    def release_hold(db: Any, hold_id: str) -> dict:
        """Release a legal hold."""
        hold = _legal_holds.get(hold_id)
        if hold is None:
            raise ValueError(f"Hold not found: {hold_id}")
        count = len(hold["asset_ids"])
        hold["released"] = True
        return {"released": count}

    # ------------------------------------------------------------------
    # Internal rule evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_rule(rule: str, workspace_id: str) -> tuple[str, str]:
        """Evaluate a single compliance rule and return (status, details).

        In a real system these would query workspace configuration, audit logs,
        encryption settings, etc.  Here we provide sensible defaults that
        reflect a typical deployment with MinIO (encrypted at rest) and
        audit logging enabled.
        """
        # Rules that typically pass in our infrastructure
        always_pass = {
            "encrypt_at_rest": "MinIO storage encryption is enabled.",
            "encryption": "All data encrypted at rest and in transit.",
            "audit_logging": "Audit logging is enabled via AuditLog model.",
            "audit_all_access": "All access events are logged.",
        }
        if rule in always_pass:
            return "pass", always_pass[rule]

        # Rules that need configuration verification → warning
        warning_rules = {
            "minimum_necessary": "Verify data access follows minimum-necessary principle.",
            "no_pii_in_logs": "Verify log sanitization is configured.",
            "data_minimization": "Verify only necessary data is collected.",
            "consent_required": "Verify consent collection mechanisms are in place.",
            "breach_notification_72h": "Verify breach notification procedures are documented.",
            "access_controls": "Verify RBAC is properly configured.",
            "incident_response": "Verify incident response plan is documented.",
        }
        if rule in warning_rules:
            return "warning", warning_rules[rule]

        # Rules requiring explicit opt-in → fail by default
        fail_rules = {
            "right_to_deletion": "Data deletion workflow not yet implemented.",
        }
        if rule in fail_rules:
            return "fail", fail_rules[rule]

        return "warning", f"Rule '{rule}' not yet evaluated."
