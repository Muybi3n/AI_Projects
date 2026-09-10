# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for AI Caregiver Medical Advocate Companion.
"""

from careguard.ai_companion import CareCompanion, build_care_context
from careguard.models import CareRecipient, DoctorVisit


def test_build_care_context():
    v = DoctorVisit(physician_name="Dr. House", specialty="Diagnostics", physician_findings="Stable condition.")
    recipient = CareRecipient(full_name="Grandma Rose", doctor_visits=[v])

    ctx = build_care_context(recipient)
    assert ctx["doctor_visits_logged"] == 1
    assert len(ctx["recent_doctor_visits"]) == 1


def test_heuristic_care_companion_doctor_query():
    v = DoctorVisit(
        physician_name="Dr. Adams", specialty="Cardiology", physician_findings="ECG normal, reduced diuretic dosage."
    )
    recipient = CareRecipient(full_name="Grandpa Joe", doctor_visits=[v])

    companion = CareCompanion()
    resp = companion.consult("What did the cardiologist say at the last visit?", recipient)

    assert len(resp.doctor_visit_takeaways) > 0
    assert "reduced diuretic dosage" in resp.doctor_visit_takeaways[0]
    assert len(resp.caregiver_action_plan) > 0


def test_custom_llm_caregiver_adapter():
    recipient = CareRecipient()

    def mock_llm(q: str, ctx: dict) -> str:
        return (
            '{"advocate_summary": "Caregiver plan ready.", "questions_for_specialist": ["Ask about physical therapy"]}'
        )

    companion = CareCompanion(custom_llm_callable=mock_llm)
    resp = companion.consult("Visit prep", recipient)

    assert resp.advocate_summary == "Caregiver plan ready."
    assert "Ask about physical therapy" in resp.questions_for_specialist
