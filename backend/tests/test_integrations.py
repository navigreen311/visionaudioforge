"""Tests for the Integration Hub — Slack, Teams, email, webhooks, storage, event bus."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.services.integrations.email import EmailIntegration
from app.services.integrations.event_bus import EventBus
from app.services.integrations.slack import SlackIntegration
from app.services.integrations.storage_connectors import (
    LocalConnector,
    S3Connector,
    StorageConnectorFactory,
)
from app.services.integrations.teams import TeamsIntegration
from app.services.integrations.webhooks import WebhookManager
from tests.db_utils import (
    db_session_factory,
    fresh_engine,
    requires_postgres,
    seed_workspace,
)


@pytest.fixture
async def webhook_env():
    """Yield (session_factory, workspace_id) — webhooks are rows now."""
    await requires_postgres()

    engine = await fresh_engine()
    factory = db_session_factory(engine)

    async with factory() as session:
        workspace_id = await seed_workspace(session, "integrations")

    try:
        yield factory, str(workspace_id)
    finally:
        await engine.dispose()


@pytest.fixture
async def webhook_db(webhook_env):
    factory, _ = webhook_env
    async with factory() as session:
        yield session


@pytest.fixture
def webhook_workspace(webhook_env):
    return webhook_env[1]


# =====================================================================
# Slack
# =====================================================================


class TestSlackMessageFormat:
    def test_format_alert_message(self):
        alert = {
            "id": "a1",
            "severity": "critical",
            "title": "CPU overload",
            "message": "CPU usage exceeded 95%",
            "timestamp": "2026-03-20T12:00:00Z",
            "source": "monitor",
        }
        blocks = SlackIntegration.format_alert_message(alert)
        assert len(blocks) == 4
        assert blocks[0]["type"] == "header"
        assert "CRITICAL" in blocks[0]["text"]["text"]
        assert blocks[1]["type"] == "section"
        assert blocks[2]["type"] == "context"
        assert blocks[3]["type"] == "actions"

    def test_format_event_notification(self):
        event = {
            "event_type": "pipeline.completed",
            "summary": "Pipeline X finished successfully",
        }
        blocks = SlackIntegration.format_event_notification(event)
        assert blocks[0]["type"] == "header"
        assert "pipeline.completed" in blocks[0]["text"]["text"]


# =====================================================================
# Teams
# =====================================================================


class TestTeamsCardFormat:
    def test_format_alert_card(self):
        alert = {
            "severity": "high",
            "title": "Disk full",
            "message": "Volume /data is at 98%",
            "timestamp": "2026-03-20T12:00:00Z",
            "source": "disk-monitor",
        }
        card = TeamsIntegration.format_alert_card(alert)
        assert card["type"] == "AdaptiveCard"
        assert any(b.get("type") == "FactSet" for b in card["body"])
        header = card["body"][0]
        assert "HIGH" in header["text"]

    def test_format_summary_card(self):
        card = TeamsIntegration.format_summary_card(
            "Daily Stats", {"alerts": 42, "pipelines_run": 7}
        )
        facts = card["body"][1]["facts"]
        assert len(facts) == 2
        assert facts[0]["title"] == "alerts"


# =====================================================================
# Email
# =====================================================================


class TestEmailFormatAlert:
    def test_format_alert_email(self):
        alert = {
            "severity": "critical",
            "title": "Service Down",
            "message": "The API gateway is unreachable.",
            "timestamp": "2026-03-20T12:00:00Z",
            "source": "health-check",
            "id": "abc",
        }
        result = EmailIntegration.format_alert_email(alert)
        assert "[CRITICAL]" in result["subject"]
        assert "Service Down" in result["subject"]
        assert "<html>" in result["html"]
        assert "CRITICAL" in result["text"]


class TestEmailStubWithoutSmtp:
    @pytest.mark.asyncio
    async def test_stub_fallback(self, monkeypatch):
        monkeypatch.delenv("SMTP_HOST", raising=False)
        monkeypatch.delenv("SENDGRID_API_KEY", raising=False)

        result = await EmailIntegration.send_email(
            to="user@example.com",
            subject="Test",
            body_html="<p>Hello</p>",
        )
        assert result["sent"] is False
        assert result["method"] == "stub"


# =====================================================================
# Webhooks
# =====================================================================


class TestWebhookRegisterAndList:
    @pytest.mark.asyncio
    async def test_register_and_list(self, webhook_db, webhook_workspace):
        reg = await WebhookManager.register_webhook(
            db=webhook_db,
            workspace_id=webhook_workspace,
            name="My Hook",
            url="https://example.com/hook",
            events=["alert.*"],
            secret="s3cr3t",
        )
        assert "webhook_id" in reg
        assert reg["events"] == ["alert.*"]

        hooks = await WebhookManager.list_webhooks(
            db=webhook_db, workspace_id=webhook_workspace
        )
        assert len(hooks) == 1
        assert hooks[0]["name"] == "My Hook"
        # Secret should NOT be exposed in list
        assert "secret" not in hooks[0]

    @pytest.mark.asyncio
    async def test_registrations_survive_a_restart(self, webhook_env):
        """A webhook registered before a restart still fires after it."""
        factory, workspace_id = webhook_env

        async with factory() as session:
            registered = await WebhookManager.register_webhook(
                db=session,
                workspace_id=workspace_id,
                name="Durable Hook",
                url="https://example.com/durable",
                events=["alert.*"],
            )

        restarted_engine = await fresh_engine()
        restarted = db_session_factory(restarted_engine)
        try:
            async with restarted() as session:
                hooks = await WebhookManager.list_webhooks(
                    db=session, workspace_id=workspace_id
                )
                assert [h["webhook_id"] for h in hooks] == [
                    registered["webhook_id"]
                ]
                assert hooks[0]["name"] == "Durable Hook"
        finally:
            await restarted_engine.dispose()

    @pytest.mark.asyncio
    async def test_list_is_workspace_scoped(self, webhook_env, webhook_db, webhook_workspace):
        """Another workspace's webhooks are not listed."""
        factory, _ = webhook_env

        await WebhookManager.register_webhook(
            db=webhook_db,
            workspace_id=webhook_workspace,
            name="Mine",
            url="https://example.com/mine",
            events=["alert.*"],
        )

        async with factory() as other_session:
            other_ws = str(await seed_workspace(other_session, "integrations-other"))
            await WebhookManager.register_webhook(
                db=other_session,
                workspace_id=other_ws,
                name="Theirs",
                url="https://example.com/theirs",
                events=["alert.*"],
            )

        hooks = await WebhookManager.list_webhooks(
            db=webhook_db, workspace_id=webhook_workspace
        )
        assert [h["name"] for h in hooks] == ["Mine"]


class TestWebhookSignature:
    def test_compute_signature(self):
        payload = '{"event":"test"}'
        secret = "mysecret"
        sig = WebhookManager.compute_signature(payload, secret)
        expected = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        assert sig == expected


class TestWebhookTrigger:
    @pytest.mark.asyncio
    async def test_trigger_matching(self, webhook_db, webhook_workspace):
        registered = await WebhookManager.register_webhook(
            db=webhook_db,
            workspace_id=webhook_workspace,
            name="Alert Hook",
            url="https://example.com/hook",
            events=["alert.*"],
        )

        with patch("app.services.integrations.webhooks.httpx.AsyncClient") as MockClient:
            mock_resp = AsyncMock()
            mock_resp.status_code = 200
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_resp)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            results = await WebhookManager.trigger_webhooks(
                db=webhook_db,
                workspace_id=webhook_workspace,
                event_type="alert.created",
                payload={"id": "a1"},
            )
            assert len(results) == 1
            assert results[0]["status"] == "sent"

        # The attempt is recorded, so the console's delivery log is real.
        log = await WebhookManager.delivery_log(
            webhook_db, registered["webhook_id"]
        )
        assert [entry["event_type"] for entry in log] == ["alert.created"]
        assert log[0]["success"] is True
        assert log[0]["status_code"] == 200


# =====================================================================
# Event Bus
# =====================================================================


class TestEventBusPublishSubscribe:
    @pytest.mark.asyncio
    async def test_in_memory_pub_sub(self):
        bus = EventBus(redis_url=None)
        received: list[dict] = []

        async def handler(msg: dict):
            received.append(msg)

        await bus.subscribe("test-channel", handler)
        await bus.publish("test-channel", "test.event", {"key": "value"})

        assert len(received) == 1
        assert received[0]["event_type"] == "test.event"

    @pytest.mark.asyncio
    async def test_emit_logs_event(self):
        """Without a session the bus still publishes to its local mirror."""
        bus = EventBus(redis_url=None)

        await bus.emit("ws-1", "alert.created", {"id": "a1"})

        events = bus.recent_events()
        assert len(events) == 1
        assert events[0]["event_type"] == "alert.created"

    @pytest.mark.asyncio
    async def test_emit_writes_durable_log(self, webhook_db, webhook_workspace):
        """With a session the event is written where every worker can see it."""
        bus = EventBus(redis_url=None)

        await bus.emit(
            webhook_workspace, "alert.created", {"id": "a1"}, db=webhook_db
        )

        stored = await EventBus.recent_events_stored(
            webhook_db, workspace_id=webhook_workspace
        )
        assert [e["event_type"] for e in stored] == ["alert.created"]
        assert stored[0]["payload"] == {"id": "a1"}


# =====================================================================
# Storage connectors
# =====================================================================


class TestS3ConnectorInit:
    def test_init_without_boto3(self):
        connector = S3Connector(
            {"bucket": "test-bucket", "region": "us-west-2"}
        )
        assert connector.bucket == "test-bucket"
        assert connector.region == "us-west-2"
        # _client may be None if boto3 not installed — that's fine


class TestLocalConnectorUploadDownload:
    @pytest.mark.asyncio
    async def test_upload_download_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            connector = LocalConnector({"root": tmpdir})

            result = await connector.upload("test/file.txt", b"hello world")
            assert result["ok"] is True

            data = await connector.download("test/file.txt")
            assert data == b"hello world"

            keys = await connector.list()
            # Normalize path separators for cross-platform compatibility
            normalized_keys = [k.replace("\\", "/") for k in keys]
            assert "test/file.txt" in normalized_keys

            deleted = await connector.delete("test/file.txt")
            assert deleted is True

            deleted_again = await connector.delete("test/file.txt")
            assert deleted_again is False

    @pytest.mark.asyncio
    async def test_download_missing_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            connector = LocalConnector({"root": tmpdir})
            with pytest.raises(FileNotFoundError):
                await connector.download("nonexistent")


class TestStorageFactory:
    def test_get_local_connector(self):
        c = StorageConnectorFactory.get_connector("local", {"root": "/tmp/test-vaf"})
        assert isinstance(c, LocalConnector)

    def test_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown storage connector"):
            StorageConnectorFactory.get_connector("azure_blob", {})


# =====================================================================
# API route tests
# =====================================================================


@pytest.fixture
async def integration_client():
    from app.main import app as main_app

    transport = ASGITransport(app=main_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestApiWebhookCrud:
    @pytest.mark.asyncio
    async def test_register_list_delete(self, webhook_env, webhook_workspace):
        from app.core.deps import get_db
        from app.main import app as main_app

        factory, _ = webhook_env

        async def _override():
            async with factory() as session:
                yield session

        main_app.dependency_overrides[get_db] = _override
        transport = ASGITransport(app=main_app)
        try:
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                # Register
                resp = await client.post(
                    "/api/integrations/webhooks",
                    json={
                        "workspace_id": webhook_workspace,
                        "name": "API Hook",
                        "url": "https://example.com/wh",
                        "events": ["alert.*"],
                    },
                )
                assert resp.status_code == 201
                wh_id = resp.json()["webhook_id"]

                # List
                resp = await client.get(
                    "/api/integrations/webhooks",
                    params={"workspace_id": webhook_workspace},
                )
                assert resp.status_code == 200
                assert len(resp.json()) == 1

                # Delete
                resp = await client.delete(f"/api/integrations/webhooks/{wh_id}")
                assert resp.status_code == 200
                assert resp.json()["deleted"] is True

                # Delete again -> 404
                resp = await client.delete(f"/api/integrations/webhooks/{wh_id}")
                assert resp.status_code == 404
        finally:
            main_app.dependency_overrides.pop(get_db, None)


class TestApiSlackSend:
    @pytest.mark.asyncio
    async def test_slack_send_endpoint(self, integration_client):
        client = integration_client
        with patch.object(
            SlackIntegration, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = {"ok": True, "status_code": 200}
            resp = await client.post(
                "/api/integrations/slack/send",
                json={
                    "webhook_url": "https://hooks.slack.com/test",
                    "message": "Hello from test",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["ok"] is True
            mock_send.assert_called_once()
