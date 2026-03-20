"""Email integration — SMTP, SendGrid, or stub delivery."""

from __future__ import annotations

import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import httpx


class EmailIntegration:
    """Send emails via SMTP, SendGrid, or a local stub."""

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    @staticmethod
    async def send_email(
        to: str | list[str],
        subject: str,
        body_html: str,
        body_text: str | None = None,
        from_addr: str | None = None,
    ) -> dict[str, Any]:
        """Try SMTP → SendGrid → stub, in that order.

        Returns ``{"sent": bool, "method": str}``.
        """
        recipients = [to] if isinstance(to, str) else to
        sender = from_addr or os.getenv("EMAIL_FROM", "noreply@vaf-platform.local")

        # --- Attempt 1: SMTP ---
        smtp_host = os.getenv("SMTP_HOST")
        if smtp_host:
            return EmailIntegration._send_smtp(
                smtp_host, sender, recipients, subject, body_html, body_text
            )

        # --- Attempt 2: SendGrid ---
        sg_key = os.getenv("SENDGRID_API_KEY")
        if sg_key:
            return await EmailIntegration._send_sendgrid(
                sg_key, sender, recipients, subject, body_html, body_text
            )

        # --- Fallback: stub ---
        return {
            "sent": False,
            "method": "stub",
            "note": (
                "No SMTP_HOST or SENDGRID_API_KEY configured. "
                "Email was not delivered."
            ),
            "to": recipients,
            "subject": subject,
        }

    # ------------------------------------------------------------------
    # SMTP transport
    # ------------------------------------------------------------------

    @staticmethod
    def _send_smtp(
        host: str,
        sender: str,
        recipients: list[str],
        subject: str,
        body_html: str,
        body_text: str | None,
    ) -> dict[str, Any]:
        port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USERNAME", "")
        password = os.getenv("SMTP_PASSWORD", "")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)

        if body_text:
            msg.attach(MIMEText(body_text, "plain"))
        msg.attach(MIMEText(body_html, "html"))

        try:
            with smtplib.SMTP(host, port) as server:
                if port == 587:
                    server.starttls()
                if username:
                    server.login(username, password)
                server.sendmail(sender, recipients, msg.as_string())
            return {"sent": True, "method": "smtp"}
        except Exception as exc:  # noqa: BLE001
            return {"sent": False, "method": "smtp", "error": str(exc)}

    # ------------------------------------------------------------------
    # SendGrid transport
    # ------------------------------------------------------------------

    @staticmethod
    async def _send_sendgrid(
        api_key: str,
        sender: str,
        recipients: list[str],
        subject: str,
        body_html: str,
        body_text: str | None,
    ) -> dict[str, Any]:
        content = [{"type": "text/html", "value": body_html}]
        if body_text:
            content.insert(0, {"type": "text/plain", "value": body_text})

        payload = {
            "personalizations": [{"to": [{"email": r} for r in recipients]}],
            "from": {"email": sender},
            "subject": subject,
            "content": content,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
            )

        return {
            "sent": resp.status_code in (200, 202),
            "method": "sendgrid",
            "status_code": resp.status_code,
        }

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def format_alert_email(alert: dict[str, Any]) -> dict[str, Any]:
        """Produce subject, HTML body, and plain-text body for an alert."""
        severity = alert.get("severity", "info").upper()
        title = alert.get("title", "Alert")
        message = alert.get("message", "")
        timestamp = alert.get("timestamp", datetime.now(timezone.utc).isoformat())
        source = alert.get("source", "unknown")
        alert_id = alert.get("id", "n/a")

        color = {
            "CRITICAL": "#dc3545",
            "HIGH": "#fd7e14",
            "MEDIUM": "#ffc107",
            "LOW": "#28a745",
            "INFO": "#17a2b8",
        }.get(severity, "#6c757d")

        html = f"""\
<html>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
  <div style="background:{color};color:#fff;padding:12px 16px;border-radius:4px 4px 0 0">
    <h2 style="margin:0">[{severity}] {title}</h2>
  </div>
  <div style="border:1px solid #ddd;border-top:none;padding:16px;border-radius:0 0 4px 4px">
    <p>{message}</p>
    <table style="width:100%;font-size:14px">
      <tr><td><b>Timestamp</b></td><td>{timestamp}</td></tr>
      <tr><td><b>Source</b></td><td>{source}</td></tr>
      <tr><td><b>Severity</b></td><td>{severity}</td></tr>
    </table>
    <p style="margin-top:16px">
      <a href="#alert-{alert_id}"
         style="background:{color};color:#fff;padding:8px 16px;text-decoration:none;border-radius:4px">
        View Alert
      </a>
    </p>
  </div>
</body>
</html>"""

        text = f"[{severity}] {title}\n\n{message}\n\nTimestamp: {timestamp}\nSource: {source}"

        return {"subject": f"[{severity}] {title}", "html": html, "text": text}

    @staticmethod
    def format_daily_digest(
        alerts: list[dict[str, Any]], stats: dict[str, Any]
    ) -> dict[str, Any]:
        """Build a daily-digest email summarising alerts and platform stats."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        total = len(alerts)

        severity_counts: dict[str, int] = {}
        for a in alerts:
            sev = a.get("severity", "info").upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        rows = "\n".join(
            f"<tr><td>{a.get('severity','').upper()}</td>"
            f"<td>{a.get('title','')}</td>"
            f"<td>{a.get('timestamp','')}</td></tr>"
            for a in alerts[:20]
        )

        stat_rows = "\n".join(
            f"<tr><td><b>{k}</b></td><td>{v}</td></tr>" for k, v in stats.items()
        )

        html = f"""\
<html>
<body style="font-family:Arial,sans-serif;max-width:700px;margin:auto">
  <h1>Daily Digest — {today}</h1>
  <h3>Summary</h3>
  <p>Total alerts: {total}</p>
  <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;width:100%">
    <tr><th>Severity</th><th>Count</th></tr>
    {"".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in severity_counts.items())}
  </table>
  <h3>Platform Stats</h3>
  <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;width:100%">
    {stat_rows}
  </table>
  <h3>Recent Alerts (up to 20)</h3>
  <table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;width:100%">
    <tr><th>Severity</th><th>Title</th><th>Timestamp</th></tr>
    {rows}
  </table>
</body>
</html>"""

        return {"subject": f"VAF Daily Digest — {today}", "html": html}
