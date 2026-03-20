"""Tests for the Healthcare & Clinical vertical pack and Medical NLP service."""

from __future__ import annotations

import pytest

from app.services.verticals.healthcare import HealthcareVerticalPack
from app.services.verticals.medical_nlp import MedicalNLPService


# ---------------------------------------------------------------------------
# HealthcareVerticalPack — pack info
# ---------------------------------------------------------------------------


class TestPackInfo:
    def test_pack_info_has_required_keys(self):
        info = HealthcareVerticalPack.PACK_INFO
        assert "name" in info
        assert "version" in info
        assert "description" in info

    def test_pack_info_name(self):
        assert HealthcareVerticalPack.PACK_INFO["name"] == "Healthcare & Clinical"

    def test_pack_info_version(self):
        assert HealthcareVerticalPack.PACK_INFO["version"] == "1.0"

    def test_pack_info_description_mentions_hipaa(self):
        assert "HIPAA" in HealthcareVerticalPack.PACK_INFO["description"]


# ---------------------------------------------------------------------------
# Pipeline templates
# ---------------------------------------------------------------------------


class TestPipelineTemplates:
    def test_returns_five_templates(self):
        templates = HealthcareVerticalPack.get_pipeline_templates()
        assert len(templates) == 5

    def test_expected_template_keys(self):
        templates = HealthcareVerticalPack.get_pipeline_templates()
        expected = {
            "patient_monitoring",
            "medical_image_analysis",
            "clinical_documentation",
            "medication_verification",
            "wound_assessment",
        }
        assert set(templates.keys()) == expected

    def test_each_template_has_definition(self):
        templates = HealthcareVerticalPack.get_pipeline_templates()
        for key, tmpl in templates.items():
            assert "definition" in tmpl, f"{key} missing definition"
            defn = tmpl["definition"]
            assert "nodes" in defn, f"{key} definition missing nodes"
            assert "edges" in defn, f"{key} definition missing edges"

    def test_each_template_has_name_and_category(self):
        templates = HealthcareVerticalPack.get_pipeline_templates()
        for key, tmpl in templates.items():
            assert "name" in tmpl, f"{key} missing name"
            assert tmpl["category"] == "Healthcare", f"{key} wrong category"

    def test_patient_monitoring_has_fall_detection(self):
        tmpl = HealthcareVerticalPack.get_pipeline_templates()["patient_monitoring"]
        node_types = [n["type"] for n in tmpl["definition"]["nodes"]]
        assert "fall_detection" in node_types

    def test_medication_verification_has_ocr(self):
        tmpl = HealthcareVerticalPack.get_pipeline_templates()["medication_verification"]
        node_types = [n["type"] for n in tmpl["definition"]["nodes"]]
        assert "ocr" in node_types


# ---------------------------------------------------------------------------
# Compliance config — HIPAA fields
# ---------------------------------------------------------------------------


class TestComplianceConfig:
    def test_standard_is_hipaa(self):
        config = HealthcareVerticalPack.get_compliance_config()
        assert config["standard"] == "HIPAA"

    def test_encrypt_at_rest(self):
        config = HealthcareVerticalPack.get_compliance_config()
        assert config["encrypt_at_rest"] is True

    def test_audit_all_access(self):
        config = HealthcareVerticalPack.get_compliance_config()
        assert config["audit_all_access"] is True

    def test_auto_pii_redaction(self):
        config = HealthcareVerticalPack.get_compliance_config()
        assert config["auto_pii_redaction"] is True

    def test_data_retention_years(self):
        config = HealthcareVerticalPack.get_compliance_config()
        assert config["data_retention_years"] == 6

    def test_minimum_necessary(self):
        config = HealthcareVerticalPack.get_compliance_config()
        assert config["minimum_necessary"] is True


# ---------------------------------------------------------------------------
# Alert presets
# ---------------------------------------------------------------------------


class TestAlertPresets:
    def test_patient_fall_is_critical(self):
        presets = HealthcareVerticalPack.get_alert_presets()
        assert presets["patient_fall"]["severity"] == "critical"

    def test_abnormal_vital_is_high(self):
        presets = HealthcareVerticalPack.get_alert_presets()
        assert presets["abnormal_vital_pattern"]["severity"] == "high"

    def test_medication_error_is_critical(self):
        presets = HealthcareVerticalPack.get_alert_presets()
        assert presets["medication_error"]["severity"] == "critical"

    def test_unauthorized_access_is_high(self):
        presets = HealthcareVerticalPack.get_alert_presets()
        assert presets["unauthorized_access_to_records"]["severity"] == "high"


# ---------------------------------------------------------------------------
# Dashboard config
# ---------------------------------------------------------------------------


class TestDashboardConfig:
    def test_has_widgets(self):
        config = HealthcareVerticalPack.get_dashboard_config()
        assert "widgets" in config
        assert len(config["widgets"]) == 4

    def test_widget_ids(self):
        config = HealthcareVerticalPack.get_dashboard_config()
        ids = {w["id"] for w in config["widgets"]}
        assert ids == {"patient_status", "active_monitors", "alert_queue", "compliance_status"}


# ---------------------------------------------------------------------------
# Report templates
# ---------------------------------------------------------------------------


class TestReportTemplates:
    def test_has_four_reports(self):
        reports = HealthcareVerticalPack.get_report_templates()
        assert len(reports) == 4

    def test_expected_report_keys(self):
        reports = HealthcareVerticalPack.get_report_templates()
        expected = {
            "patient_incident_report",
            "daily_ward_summary",
            "compliance_audit",
            "clinical_study_export",
        }
        assert set(reports.keys()) == expected


# ---------------------------------------------------------------------------
# Model configs
# ---------------------------------------------------------------------------


class TestModelConfigs:
    def test_anomaly_detection_high_sensitivity(self):
        configs = HealthcareVerticalPack.get_model_configs()
        assert configs["anomaly_detection"]["sensitivity"] == "high"

    def test_pii_scanner_strict(self):
        configs = HealthcareVerticalPack.get_model_configs()
        assert configs["pii_scanner"]["mode"] == "strict"


# ---------------------------------------------------------------------------
# Medical NLP — term extraction
# ---------------------------------------------------------------------------


class TestMedicalTermExtraction:
    def test_extract_drug(self):
        terms = MedicalNLPService.extract_medical_terms("Patient takes aspirin daily.")
        drug_terms = [t for t in terms if t["type"] == "drug"]
        assert len(drug_terms) >= 1
        assert drug_terms[0]["term"].lower() == "aspirin"

    def test_extract_dosage(self):
        terms = MedicalNLPService.extract_medical_terms("Prescribed 500mg twice daily.")
        dosage_terms = [t for t in terms if t["type"] == "dosage"]
        assert len(dosage_terms) >= 1
        assert "500mg" in dosage_terms[0]["term"]

    def test_extract_condition(self):
        terms = MedicalNLPService.extract_medical_terms("History of diabetes and hypertension.")
        conditions = [t for t in terms if t["type"] == "condition"]
        names = [c["term"].lower() for c in conditions]
        assert "diabetes" in names
        assert "hypertension" in names

    def test_extract_procedure(self):
        terms = MedicalNLPService.extract_medical_terms("Scheduled for MRI tomorrow.")
        procedures = [t for t in terms if t["type"] == "procedure"]
        assert len(procedures) >= 1

    def test_extract_anatomy(self):
        terms = MedicalNLPService.extract_medical_terms("Pain in the liver region.")
        anatomy = [t for t in terms if t["type"] == "anatomy"]
        assert len(anatomy) >= 1
        assert anatomy[0]["term"].lower() == "liver"

    def test_position_returned(self):
        text = "Take aspirin daily."
        terms = MedicalNLPService.extract_medical_terms(text)
        for t in terms:
            assert "position" in t
            start, end = t["position"]
            assert text[start:end] == t["term"]


# ---------------------------------------------------------------------------
# Medical NLP — clinical note structuring
# ---------------------------------------------------------------------------


class TestClinicalNoteStructuring:
    def test_structure_with_headers(self):
        transcript = (
            "CC: Chest pain. "
            "HPI: Patient reports 2 days of chest pain. "
            "Assessment: Likely angina. "
            "Plan: Order stress test."
        )
        result = MedicalNLPService.structure_clinical_note(transcript)
        assert "chief_complaint" in result
        assert "history" in result
        assert "assessment" in result
        assert "plan" in result

    def test_chief_complaint_parsed(self):
        transcript = "CC: Headache and dizziness. HPI: Onset 3 days ago."
        result = MedicalNLPService.structure_clinical_note(transcript)
        assert "Headache" in result["chief_complaint"] or "headache" in result["chief_complaint"].lower()

    def test_no_headers_fallback(self):
        transcript = "Patient complains of back pain."
        result = MedicalNLPService.structure_clinical_note(transcript)
        assert result["chief_complaint"] == transcript.strip()

    def test_all_keys_present(self):
        transcript = "CC: Fever. Assessment: Viral infection. Plan: Rest and fluids."
        result = MedicalNLPService.structure_clinical_note(transcript)
        assert set(result.keys()) == {"chief_complaint", "history", "assessment", "plan"}


# ---------------------------------------------------------------------------
# Medical NLP — de-identification
# ---------------------------------------------------------------------------


class TestDeidentification:
    def test_redact_mrn(self):
        text = "Patient MRN: 12345678 admitted today."
        result = MedicalNLPService.deidentify_text(text)
        assert "12345678" not in result
        assert "[REDACTED]" in result

    def test_redact_date(self):
        text = "Visit on 01/15/2025 for follow-up."
        result = MedicalNLPService.deidentify_text(text)
        assert "01/15/2025" not in result
        assert "[REDACTED]" in result

    def test_redact_patient_name(self):
        text = "Dr. John Smith ordered labs."
        result = MedicalNLPService.deidentify_text(text)
        assert "John Smith" not in result
        assert "[REDACTED]" in result

    def test_preserves_non_pii_text(self):
        text = "Patient diagnosed with diabetes."
        result = MedicalNLPService.deidentify_text(text)
        assert result == text


# ---------------------------------------------------------------------------
# API — install pack (integration-style test)
# ---------------------------------------------------------------------------


class TestInstallPack:
    def test_install_pack_returns_all_components(self):
        """Simulate installing the healthcare vertical pack."""
        pack = HealthcareVerticalPack()

        installed = {
            "pack_info": pack.PACK_INFO,
            "pipelines": pack.get_pipeline_templates(),
            "alerts": pack.get_alert_presets(),
            "compliance": pack.get_compliance_config(),
            "dashboard": pack.get_dashboard_config(),
            "reports": pack.get_report_templates(),
            "models": pack.get_model_configs(),
        }

        assert installed["pack_info"]["name"] == "Healthcare & Clinical"
        assert len(installed["pipelines"]) == 5
        assert len(installed["alerts"]) == 4
        assert installed["compliance"]["standard"] == "HIPAA"
        assert len(installed["dashboard"]["widgets"]) == 4
        assert len(installed["reports"]) == 4
        assert len(installed["models"]) == 2
