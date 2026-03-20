"""Comprehensive tests for all 7 vertical starter packs and the installer."""

from __future__ import annotations

import pytest

from app.services.verticals.base import VerticalPack
from app.services.verticals.callcenter import CallCenterVerticalPack
from app.services.verticals.education import EducationVerticalPack
from app.services.verticals.healthcare import HealthcareVerticalPack
from app.services.verticals.industrial import IndustrialVerticalPack
from app.services.verticals.installer import (
    AVAILABLE_PACKS,
    get_pack,
    install_pack,
    is_installed,
    list_available_packs,
    reset,
    uninstall_pack,
)
from app.services.verticals.media import MediaVerticalPack
from app.services.verticals.retail import RetailVerticalPack
from app.services.verticals.security import SecurityVerticalPack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALL_PACK_CLASSES: list[type[VerticalPack]] = [
    SecurityVerticalPack,
    HealthcareVerticalPack,
    CallCenterVerticalPack,
    RetailVerticalPack,
    IndustrialVerticalPack,
    MediaVerticalPack,
    EducationVerticalPack,
]

ALL_SLUGS = ["security", "healthcare", "callcenter", "retail", "industrial", "media", "education"]


@pytest.fixture(autouse=True)
def _clean_installer():
    """Reset installer state before each test."""
    reset()
    yield
    reset()


# ===================================================================
# Per-pack structural tests (parametrised across all 7 packs)
# ===================================================================


@pytest.mark.parametrize("PackClass", ALL_PACK_CLASSES)
class TestPackStructure:
    """Every vertical pack must satisfy the same structural contract."""

    def test_pack_info_valid(self, PackClass: type[VerticalPack]):
        pack = PackClass()
        info = pack.info()
        assert isinstance(info, dict)
        for key in ("name", "slug", "icon", "description", "category"):
            assert key in info, f"Missing key '{key}' in info()"
            assert isinstance(info[key], str) and len(info[key]) > 0

    def test_pipelines_have_nodes_and_edges(self, PackClass: type[VerticalPack]):
        pack = PackClass()
        pipelines = pack.pipelines()
        assert isinstance(pipelines, dict)
        assert len(pipelines) > 0, "Pack must have at least one pipeline"
        for slug, pipeline in pipelines.items():
            assert "nodes" in pipeline, f"Pipeline '{slug}' missing 'nodes'"
            assert "edges" in pipeline, f"Pipeline '{slug}' missing 'edges'"
            assert len(pipeline["nodes"]) >= 2, f"Pipeline '{slug}' needs >=2 nodes"
            assert len(pipeline["edges"]) >= 1, f"Pipeline '{slug}' needs >=1 edge"
            # Every node must have id and type
            for node in pipeline["nodes"]:
                assert "id" in node and "type" in node

    def test_alert_presets_have_conditions(self, PackClass: type[VerticalPack]):
        pack = PackClass()
        presets = pack.alert_presets()
        assert isinstance(presets, dict)
        assert len(presets) > 0, "Pack must have at least one alert preset"
        for slug, preset in presets.items():
            assert "name" in preset, f"Preset '{slug}' missing 'name'"
            assert "severity" in preset, f"Preset '{slug}' missing 'severity'"
            assert "conditions" in preset, f"Preset '{slug}' missing 'conditions'"
            assert isinstance(preset["conditions"], dict)


# ===================================================================
# Installer tests
# ===================================================================


class TestInstaller:
    """Tests for the vertical pack installer module."""

    def test_installer_lists_all_7_packs(self):
        available = list_available_packs()
        slugs = [p["slug"] for p in available]
        assert len(slugs) == 7
        for expected in ALL_SLUGS:
            assert expected in slugs, f"Missing pack '{expected}' in available list"

    def test_available_packs_registry_has_7(self):
        assert len(AVAILABLE_PACKS) == 7

    def test_install_and_uninstall(self):
        # Install
        result = install_pack("retail")
        assert result["slug"] == "retail"
        assert result["pipelines_installed"] == 5
        assert result["alert_presets_installed"] == 4
        assert is_installed("retail")

        # Uninstall
        removed = uninstall_pack("retail")
        assert removed is True
        assert not is_installed("retail")

        # Uninstalling again returns False
        assert uninstall_pack("retail") is False

    def test_install_unknown_pack_raises(self):
        with pytest.raises(KeyError, match="Unknown vertical pack"):
            install_pack("nonexistent_pack")

    def test_get_pack_returns_instance(self):
        pack = get_pack("industrial")
        assert pack is not None
        assert isinstance(pack, IndustrialVerticalPack)

    def test_get_pack_unknown_returns_none(self):
        assert get_pack("does_not_exist") is None

    def test_install_all_packs(self):
        for slug in ALL_SLUGS:
            result = install_pack(slug)
            assert result["pipelines_installed"] > 0
            assert result["alert_presets_installed"] > 0
        assert len(list_available_packs()) == 7
        for p in list_available_packs():
            assert p["installed"] is True


# ===================================================================
# Specific pipeline smoke tests
# ===================================================================


class TestRetailCustomerCountingPipeline:
    """Validate the retail customer-counting pipeline structure."""

    def test_retail_customer_counting_pipeline(self):
        pack = RetailVerticalPack()
        pipelines = pack.pipelines()
        assert "customer_counting" in pipelines
        pipeline = pipelines["customer_counting"]
        node_types = [n["type"] for n in pipeline["nodes"]]
        assert "input_video" in node_types
        assert "detect_objects" in node_types
        assert "save_asset" in node_types
        assert len(pipeline["edges"]) >= 3


class TestIndustrialSafetyPipeline:
    """Validate the industrial safety-compliance pipeline structure."""

    def test_industrial_safety_pipeline(self):
        pack = IndustrialVerticalPack()
        pipelines = pack.pipelines()
        assert "safety_compliance" in pipelines
        pipeline = pipelines["safety_compliance"]
        node_types = [n["type"] for n in pipeline["nodes"]]
        assert "detect_objects" in node_types
        assert "conditional" in node_types
        assert "alert" in node_types
        # Must have PPE-related alert message
        alert_nodes = [n for n in pipeline["nodes"] if n["type"] == "alert"]
        assert any("PPE" in n["params"].get("message", "") for n in alert_nodes)


class TestMediaHighlightPipeline:
    """Validate the media auto-highlight pipeline structure."""

    def test_media_highlight_pipeline(self):
        pack = MediaVerticalPack()
        pipelines = pack.pipelines()
        assert "auto_highlight" in pipelines
        pipeline = pipelines["auto_highlight"]
        node_types = [n["type"] for n in pipeline["nodes"]]
        assert "input_video" in node_types
        assert "frame_diff" in node_types
        assert "save_asset" in node_types
        assert len(pipeline["edges"]) >= 3


class TestEducationLecturePipeline:
    """Validate the education lecture-analysis pipeline structure."""

    def test_education_lecture_pipeline(self):
        pack = EducationVerticalPack()
        pipelines = pack.pipelines()
        assert "lecture_analysis" in pipelines
        pipeline = pipelines["lecture_analysis"]
        node_types = [n["type"] for n in pipeline["nodes"]]
        assert "input_audio" in node_types
        assert "mfcc" in node_types
        assert "save_asset" in node_types
