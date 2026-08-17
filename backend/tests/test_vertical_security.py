"""Tests for the Security & Surveillance vertical pack, installer, reports, and API routes."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.verticals import VERTICAL_PACKS
from app.services.verticals import installer
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
    """Report templates take a session but do not query it yet."""
    return None


@pytest.fixture(autouse=True)
def _clear_installed():
    """Reset installer state between tests."""
    installer.reset()
    yield
    installer.reset()


@pytest.fixture
def pack():
    return SecurityVerticalPack()


# ---------------------------------------------------------------------------
# SecurityVerticalPack unit tests
# ---------------------------------------------------------------------------

class TestSecurityPackInfo:
    def test_info_identifies_the_pack(self, pack):
        """Pack metadata carries the slug the installer and routes key on."""
        info = pack.info()
        assert info["slug"] == "security"
        assert info["name"]
        assert info["category"]

    def test_pack_is_registered(self):
        """The security pack must be discoverable by slug."""
        assert "security" in VERTICAL_PACKS
        assert VERTICAL_PACKS["security"] is SecurityVerticalPack


class TestSecurityPackPipelines:
    def test_pipelines_are_well_formed(self, pack):
        """Every pipeline is a node/edge graph the pipeline engine can load."""
        pipelines = pack.pipelines()
        assert pipelines, "security pack ships no pipelines"

        for slug, definition in pipelines.items():
            assert definition["name"], f"{slug} has no display name"
            assert len(definition["nodes"]) >= 3, f"{slug} is trivially short"
            assert definition["edges"], f"{slug} has nodes but no edges"

    def test_pipeline_edges_reference_real_nodes(self, pack):
        """A dangling edge would fail at run time, not load time — catch it here."""
        for slug, definition in pack.pipelines().items():
            node_ids = {n["id"] for n in definition["nodes"]}
            for edge in definition["edges"]:
                assert edge["from"] in node_ids, f"{slug}: edge from unknown node"
                assert edge["to"] in node_ids, f"{slug}: edge to unknown node"

    def test_perimeter_monitoring_pipeline(self, pack):
        """Perimeter monitoring reads video, detects objects, and raises an alert."""
        perimeter = pack.pipelines()["perimeter_monitoring"]
        node_types = [n["type"] for n in perimeter["nodes"]]
        assert "input_video" in node_types
        assert "detect_objects" in node_types
        assert "alert" in node_types


class TestSecurityAlertPresets:
    def test_alert_presets_are_well_formed(self, pack):
        """Presets need a severity so the alert engine can route them."""
        presets = pack.alert_presets()
        assert presets, "security pack ships no alert presets"

        for slug, preset in presets.items():
            assert preset.get("severity") in {
                "critical",
                "high",
                "medium",
                "low",
                "warning",
                "info",
            }, f"{slug} has no usable severity"

    def test_intrusion_preset_is_critical(self, pack):
        """Intrusion is the pack's highest-stakes preset."""
        presets = pack.alert_presets()
        assert "intrusion_detected" in presets
        assert presets["intrusion_detected"]["severity"] == "critical"


class TestDashboardAndReports:
    def test_dashboard_widgets(self, pack):
        """Widgets must declare a type for the dashboard renderer."""
        widgets = pack.dashboard_widgets()
        assert widgets, "security pack ships no dashboard widgets"
        for widget in widgets:
            assert widget.get("type")

    def test_reports(self, pack):
        """Report templates are keyed by slug."""
        reports = pack.reports()
        assert reports
        for slug, report in reports.items():
            assert report.get("name"), f"{slug} report has no name"


# ---------------------------------------------------------------------------
# Installer tests
# ---------------------------------------------------------------------------

class TestInstaller:
    def test_install_pack_reports_provisioned_resources(self, pack):
        """Install counts match what the pack actually defines."""
        result = installer.install_pack("security")

        assert result["slug"] == "security"
        assert result["pipelines_installed"] == len(pack.pipelines())
        assert result["alert_presets_installed"] == len(pack.alert_presets())
        assert result["dashboard_widgets"] == len(pack.dashboard_widgets())
        assert result["reports_installed"] == len(pack.reports())

    def test_install_marks_pack_installed(self):
        """State is observable through is_installed / get_installed_packs."""
        assert installer.is_installed("security") is False
        installer.install_pack("security")
        assert installer.is_installed("security") is True
        assert "security" in installer.get_installed_packs()

    def test_uninstall_removes(self):
        """Uninstalling drops the pack from the installed set."""
        installer.install_pack("security")
        assert installer.uninstall_pack("security") is True
        assert installer.is_installed("security") is False
        assert installer.get_installed_packs() == {}

    def test_uninstall_nonexistent_returns_false(self):
        """Uninstalling a pack that was never installed is a no-op."""
        assert installer.uninstall_pack("security") is False

    def test_list_available_packs_flags_installed(self):
        """The catalogue reports install state per pack."""
        installer.install_pack("security")
        packs = installer.list_available_packs()

        security = next(p for p in packs if p["slug"] == "security")
        assert security["installed"] is True
        assert all(
            p["installed"] is False for p in packs if p["slug"] != "security"
        )

    def test_get_pack_returns_instance(self):
        """get_pack resolves a slug to a usable pack instance."""
        assert isinstance(installer.get_pack("security"), SecurityVerticalPack)
        assert installer.get_pack("nonexistent") is None

    def test_install_unknown_pack_raises(self):
        """Installing an unknown slug is an error, not a silent no-op."""
        with pytest.raises(KeyError, match="Unknown vertical pack"):
            installer.install_pack("nonexistent")


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
        """GET /api/verticals/packs should return available packs."""
        resp = await client.get("/api/verticals/packs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(p["id"] == "security" for p in data)

    @pytest.mark.anyio
    async def test_api_pack_details(self, client):
        """GET /api/verticals/packs/security should return pack details."""
        resp = await client.get("/api/verticals/packs/security")
        assert resp.status_code == 200
        assert resp.json()["id"] == "security"

    @pytest.mark.anyio
    async def test_api_pack_resources(self, client):
        """GET /api/verticals/packs/security/resources lists what installs."""
        resp = await client.get("/api/verticals/packs/security/resources")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_api_pack_not_found(self, client):
        """GET /api/verticals/packs/nonexistent should 404."""
        resp = await client.get("/api/verticals/packs/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.anyio
    async def test_api_install(self, client):
        """POST /api/verticals/install starts a job the console can then poll."""
        resp = await client.post(
            "/api/verticals/install", json={"pack_id": "security"},
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        status = await client.get(f"/api/verticals/install/{job_id}/status")
        assert status.status_code == 200
        assert status.json()["pack_id"] == "security"

    @pytest.mark.anyio
    async def test_api_install_unknown_pack_404s(self, client):
        """Installing a pack that does not exist is a 404, not a silent job."""
        resp = await client.post(
            "/api/verticals/install", json={"pack_id": "nonexistent"},
        )
        assert resp.status_code == 404
