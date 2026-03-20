"""Alert service package — rule engine, incident management, and action execution."""

from app.services.alerts.alert_service import (
    AlertService,
    EscalationPolicy,
    RuleEvaluationEngine,
    auto_severity_scoring,
    deduplicate_alert,
    get_rule_engine,
)
from app.services.alerts.actions import (
    AlertActionExecutor,
    send_discord,
    send_email,
    send_slack,
    send_sms_stub,
    send_webhook,
)

__all__ = [
    "AlertService",
    "AlertActionExecutor",
    "EscalationPolicy",
    "RuleEvaluationEngine",
    "auto_severity_scoring",
    "deduplicate_alert",
    "get_rule_engine",
    "send_discord",
    "send_email",
    "send_slack",
    "send_sms_stub",
    "send_webhook",
]
