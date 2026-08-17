"""Tests for the Security & Surveillance vertical pack, installer, reports, and API routes."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.verticals.installer import VerticalInstaller
from app.services.verticals.report_templates import ReportTemplateService
from app.services.verticals.security import SecurityVerticalPack


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def workspace_id():
    return uuid.UUID("00000000-0000-0000-0000-000000000099")


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def _clear_installed():
    """Reset installer state between tests."""
    VerticalInstaller._installed.clear()
    yield
    VerticalInstaller._installed.clear()


# ---------------------------------------------------------------------------
# SecurityVerticalPack unit tests
# ---------------------------------------------------------------------------

class TestSecurityPackPipelines:
    def test_security_pack_pipelines_valid(self):
        """All five pipeline templates should be returned with correct structure."""
        pipelines = SecurityVerticalPack.get_pipeline_templates()
        assert len(pipelines) == 5
        names = {p["name"] for p in pipelines}
        assert names == {
            "perimeter_monitoring",
            "intrusion_detection",
            "loitering_detection",
            "vehicle_monitoring",
            "crowd_density",
        }
        for p in pipelines:
            assert "steps" in p
            assert len(p["steps"]) >= 3

    def test_perimeter_monitoring_pipeline(self):
        """Perimeter pipeline should detect persons and vehicles with motion filter."""
        pipelines = SecurityVerticalPack.get_pipeline_templates()
        perimeter = next(p for p in pipelines if p["name"] == "perimeter_monitoring")
        step_types = [s["type"] for s in perimeter["steps"]]
        assert "InputVideo" in step_types
        assert "DetectObjects" in step_types
        assert "Alert" in step_types


class TestSecurityAlertPresets:
    def test_security_alert_presets(self):
        """Alert presets should contain the expected rules."""
        presets = SecurityVerticalPack.get_alert_presets()
        assert len(presets) == 3
        names = {p["name"] for p in presets}
        assert "unauthorized_access" in names
        assert "camera_tampering" in names
        assert "unusual_activity" in names

    def test_unauthorized_access_preset(self):
        """Unauthorized access preset should be critical with webhook+slack actions."""
        presets = SecurityVerticalPack.get_alert_presets()
        ua = next(p for p in presets if p["name"] == "unauthorized_access")
        assert ua["severity"] == "critical"
        assert "webhook" in ua["actions"]
        assert "slack" in ua["actions"]


class TestDashboardConfig:
    def test_dashboard_config(self):
        """Dashboard should contain required widgets and KPIs."""
        config = SecurityVerticalPack.get_dashboard_config()
        assert "widgets" in config
        assert "kpis" in config
        widget_types = {w["type"] for w in config["widgets"]}
        assert "live_feed_grid" in widget_types
        assert "incident_queue" in widget_types
        assert len(config["kpis"]) >= 3


class TestModelConfigs:
    def test_model_configs(self):
        """Model configs should include object_detection and anomaly settings."""
        configs = SecurityVerticalPack.get_model_configs()
        assert "object_detection" in configs
        assert configs["object_detection"]["model"] == "yolov8n"
        assert configs["object_detection"]["confidence"] == 0.6
        assert "person" in configs["object_detection"]["classes"]
        assert "anomaly" in configs
        assert configs["anomaly"]["sensitivity"] == "high"


# ---------------------------------------------------------------------------
# Installer tests
# ---------------------------------------------------------------------------

class TestInstaller:
    @pytest.mark.anyio
    async def test_install_pack_creates_resources(self, mock_db, workspace_id):
        """Installing the security pack should report created resources."""
        result = await VerticalInstaller.install_pack(mock_db, workspace_id, "security")
        assert result["installed"] is True
        assert result["pipelines_created"] == 5
        assert result["rules_created"] == 3
        assert result["configs_applied"] >= 2

    @pytest.mark.anyio
    async def test_uninstall_removes(self, mock_db, workspace_id):
        """Uninstalling should remove the pack from the workspace."""
        await VerticalInstaller.install_pack(mock_db, workspace_id, "security")
        result = await VerticalInstaller.uninstall_pack(mock_db, workspace_id, "security")
        assert result["removed"] is True
        installed = await VerticalInstaller.list_installed_packs(mock_db, workspace_id)
        assert len(installed) == 0

    @pytest.mark.anyio
    async def test_uninstall_nonexistent_returns_false(self, mock_db, workspace_id):
        """Uninstalling a pack that is not installed should return removed=False."""
        result = await VerticalInstaller.uninstall_pack(mock_db, workspace_id, "security")
        assert result["removed"] is False

    @pytest.mark.anyio
    async def test_list_available_packs(self):
        """Should list all registered packs."""
        packs = await VerticalInstaller.list_available_packs()
        assert len(packs) >= 1
        names = {p["pack_name"] for p in packs}
        assert "security" in names

    @pytest.mark.anyio
    async def test_get_pack_info(self):
        """get_pack_info should return full details."""
        info = await VerticalInstaller.get_pack_info("security")
        assert "info" in info
        assert "pipelines" in info
        assert "alert_presets" in info
        assert "dashboard" in info

    @pytest.mark.anyio
    async def test_install_unknown_pack_raises(self, mock_db, workspace_id):
        """Installing an unknown pack should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown vertical pack"):
            await VerticalInstaller.install_pack(mock_db, workspace_id, "nonexistent")


# ---------------------------------------------------------------------------
# Report template tests
# ---------------------------------------------------------------------------

class TestReportTemplates:
    @pytest.mark.anyio
    async def test_daily_summary_report(self, mock_db, workspace_id):
        """Daily summary should return the expected structure."""
        report = await ReportTemplateService.generate_daily_summary(
            mock_db, workspace_id, "2026-03-20",
        )
        assert report["date"] == "2026-03-20"
        assert "total_alerts" in report
        assert "by_severity" in report
        assert "incidents" in report
        assert "response_times" in report
        assert "camera_uptime" in report
        assert "recommendations" in report

    @pytest.mark.anyio
    async def test_incident_report(self, mock_db):
        """Incident report should return the expected structure."""
        report = await ReportTemplateService.generate_incident_report(
            mock_db, "INC-001",
        )
        assert report["incident_id"] == "INC-001"
        assert "timeline" in report
        assert "evidence" in report
        assert "resolution" in report

    @pytest.mark.anyio
    async def test_compliance_audit(self, mock_db, workspace_id):
        """Compliance audit should include checks and pass_rate."""
        report = await ReportTemplateService.generate_compliance_audit(
            mock_db, workspace_id,
        )
        assert "audit_date" in report
        assert "checks" in report
        assert report["pass_rate"] == 1.0
        assert isinstance(report["issues"], list)


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------

class TestAPIRoutes:
    @pytest.mark.anyio
    async def test_api_list_packs(self, client):
        """GET /api/verticals should return available packs."""
        resp = await client.get("/api/verticals")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(p["pack_name"] == "security" for p in data)

    @pytest.mark.anyio
    async def test_api_pack_details(self, client):
        """GET /api/verticals/security should return pack details."""
        resp = await client.get("/api/verticals/security")
        assert resp.status_code == 200
        data = resp.json()
        assert "pipelines" in data
        assert "alert_presets" in data

    @pytest.mark.anyio
    async def test_api_pack_not_found(self, client):
        """GET /api/verticals/nonexistent should 404."""
        resp = await client.get("/api/verticals/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_api_install(self, client):
        """POST /api/verticals/security/install should install the pack."""
        ws = "00000000-0000-0000-0000-000000000001"
        resp = await client.post(f"/api/verticals/security/install?workspace_id={ws}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["installed"] is True
        assert data["pipelines_created"] == 5
