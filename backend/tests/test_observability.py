"""Tests for the observability module — dashboard, SLA, alert analytics."""

from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.observability.dashboard import SREDashboardService
from app.services.observability.sla import SLAService, STANDARD_SLAS
from app.services.observability.alert_analytics import AlertAnalytics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class _FakeDB:
    """Minimal async-session stand-in for unit tests."""

    async def execute(self, stmt):
        class _Result:
            def scalar(self):
                return 1

        return _Result()


@pytest.fixture
def fake_db():
    return _FakeDB()


# ---------------------------------------------------------------------------
# SREDashboardService — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_system_overview_returns_all_fields(fake_db):
    result = await SREDashboardService.get_system_overview(fake_db)
    expected_keys = {
        "api_status",
        "db_status",
        "redis_status",
        "uptime_s",
        "total_requests_24h",
        "error_rate_24h",
        "avg_latency_ms",
        "p99_latency_ms",
    }
    assert expected_keys.issubset(result.keys())
    assert result["api_status"] == "healthy"
    assert isinstance(result["uptime_s"], float)
    assert isinstance(result["total_requests_24h"], int)


@pytest.mark.anyio
async def test_error_taxonomy(fake_db):
    result = await SREDashboardService.get_error_taxonomy(fake_db, hours=24)
    assert "total_errors" in result
    assert "by_type" in result
    assert "by_endpoint" in result
    assert "top_errors" in result
    assert isinstance(result["top_errors"], list)
    if result["top_errors"]:
        entry = result["top_errors"][0]
        assert "error" in entry
        assert "count" in entry
        assert "last_seen" in entry


# ---------------------------------------------------------------------------
# SLAService — unit tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_sla_compliance_check(fake_db):
    config = SLAService.define_sla("test", target_uptime=99.0, max_latency_ms=1000, max_error_rate=0.1)
    result = await SLAService.check_sla_compliance(fake_db, config, period_hours=24)
    assert "compliant" in result
    assert isinstance(result["compliant"], bool)
    assert "uptime_pct" in result
    assert "avg_latency_ms" in result
    assert "error_rate" in result
    assert "violations" in result
    assert isinstance(result["violations"], list)


@pytest.mark.anyio
async def test_sla_report_generation(fake_db):
    result = await SLAService.generate_sla_report(fake_db, period="weekly")
    assert result["period"] == "weekly"
    assert "start" in result
    assert "end" in result
    assert "uptime" in result
    assert "latency_p50" in result
    assert "latency_p99" in result
    assert "incidents" in result
    assert "compliance" in result


def test_standard_slas_structure():
    for tier in ("basic", "standard", "premium"):
        assert tier in STANDARD_SLAS
        sla = STANDARD_SLAS[tier]
        assert "uptime" in sla
        assert "latency" in sla
        assert "error_rate" in sla


# ---------------------------------------------------------------------------
# AlertAnalytics — unit tests
# ---------------------------------------------------------------------------

WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.anyio
async def test_alert_fatigue_analysis(fake_db):
    result = await AlertAnalytics.analyze_alert_fatigue(fake_db, WORKSPACE_ID, days=30)
    assert "total_alerts" in result
    assert "acknowledged_pct" in result
    assert "avg_response_time_s" in result
    assert "noisy_rules" in result
    assert "fatigue_score" in result
    assert 0 <= result["fatigue_score"] <= 100
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)


@pytest.mark.anyio
async def test_rule_tuning_reports_unavailable_without_a_rule(fake_db):
    """With no readable rule there is no threshold to tune against.

    The previous version of this test asserted suggested > current, which only
    held because both numbers were generated with random.uniform. Reporting an
    invented "current threshold" would misstate the user's own configuration.
    """
    rule_id = UUID("00000000-0000-0000-0000-000000000002")
    result = await AlertAnalytics.suggest_rule_tuning(fake_db, rule_id)
    assert result["status"] == "unavailable"
    assert result["current_threshold"] is None
    assert result["suggested_threshold"] is None
    assert "reason" in result


@pytest.mark.anyio
async def test_rule_tuning_raises_the_rule_s_own_threshold():
    """A real threshold is read from the rule and raised by the policy bump."""
    rule_id = UUID("00000000-0000-0000-0000-000000000002")

    class _Rule:
        conditions = {"threshold": 80}

    class _DBWithRule:
        async def execute(self, stmt):
            class _Result:
                def scalar_one_or_none(self):
                    return _Rule()

            return _Result()

    result = await AlertAnalytics.suggest_rule_tuning(_DBWithRule(), rule_id)
    assert result["status"] == "suggested"
    assert result["current_threshold"] == 80.0
    assert result["suggested_threshold"] > result["current_threshold"]


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_api_dashboard(client):
    resp = await client.get("/api/observability/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "api_status" in data
    assert "uptime_s" in data


@pytest.mark.anyio
async def test_api_sla(client):
    resp = await client.get("/api/observability/sla?tier=standard")
    assert resp.status_code == 200
    data = resp.json()
    assert "compliant" in data
    assert "violations" in data


@pytest.mark.anyio
async def test_api_sla_report(client):
    resp = await client.post("/api/observability/sla/report?period=weekly")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period"] == "weekly"


@pytest.mark.anyio
async def test_api_pipeline_health(client):
    resp = await client.get("/api/observability/pipeline-health")
    assert resp.status_code == 200
    assert "runs_24h" in resp.json()


@pytest.mark.anyio
async def test_api_inference(client):
    resp = await client.get("/api/observability/inference")
    assert resp.status_code == 200
    assert "models_loaded" in resp.json()


@pytest.mark.anyio
async def test_api_errors(client):
    resp = await client.get("/api/observability/errors")
    assert resp.status_code == 200
    assert "total_errors" in resp.json()


@pytest.mark.anyio
async def test_api_queues(client):
    resp = await client.get("/api/observability/queues")
    assert resp.status_code == 200
    assert "celery_active" in resp.json()
