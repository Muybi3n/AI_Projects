# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for AI Healthcare Companion.
"""

from medcadence.advisor import HealthAdvisor, build_health_context
from medcadence.models import BiomarkerRecord, HealthProfile, MedicationItem


def test_build_health_context():
    b = BiomarkerRecord(name="Triglycerides", value=180.0, ref_low=0.0, ref_high=150.0)
    m = MedicationItem(name="Lipitor", dosage="20mg")
    profile = HealthProfile(biomarkers=[b], medications=[m])

    ctx = build_health_context(profile)
    assert ctx["total_biomarkers_logged"] == 1
    assert len(ctx["active_medications"]) == 1


def test_heuristic_advisor_lab_query():
    b = BiomarkerRecord(name="Triglycerides", value=180.0, ref_low=0.0, ref_high=150.0)
    profile = HealthProfile(biomarkers=[b])

    advisor = HealthAdvisor()
    resp = advisor.consult("What do my blood tests indicate?", profile)

    assert len(resp.abnormal_biomarkers) == 1
    assert "Triglycerides" in resp.abnormal_biomarkers[0]
    assert len(resp.questions_for_physician) > 0


def test_custom_llm_adapter():
    profile = HealthProfile()

    def mock_llm(q: str, ctx: dict) -> str:
        return '{"clinical_synthesis": "Healthy metabolic baseline.", "questions_for_physician": ["Check vitamin D"]}'

    advisor = HealthAdvisor(custom_llm_callable=mock_llm)
    resp = advisor.consult("How are my labs?", profile)

    assert resp.clinical_synthesis == "Healthy metabolic baseline."
    assert "Check vitamin D" in resp.questions_for_physician
