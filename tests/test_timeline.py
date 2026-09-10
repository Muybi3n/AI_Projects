# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for longitudinal clinical timeline generation.
"""

from careguard.models import CareRecipient, DoctorVisit
from careguard.timeline import ClinicalTimelineEngine


def test_clinical_timeline_generation():
    v1 = DoctorVisit(
        date="2026-01-15", physician_name="Dr. Smith", specialty="Cardiology", physician_findings="Initial consult."
    )
    v2 = DoctorVisit(
        date="2026-06-20",
        physician_name="Dr. Chen",
        specialty="Neurology",
        physician_findings="Mild cognitive decline.",
    )

    recipient = CareRecipient(full_name="Alice Miller", doctor_visits=[v1, v2])
    timeline = ClinicalTimelineEngine.build_timeline(recipient)

    assert timeline.total_encounters == 2
    assert timeline.first_recorded_encounter == "2026-01-15"
    assert timeline.latest_recorded_encounter == "2026-06-20"
    assert len(timeline.encounters) == 2
    assert timeline.encounters[0].physician == "Dr. Smith"
