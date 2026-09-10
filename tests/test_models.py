# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for caregiver models and patient serialization.
"""

from careguard.models import (
    CareRecipient,
    DailyVitalsLog,
    DoctorVisit,
    MedicationSchedule,
    PhysicianContact,
    TimingSlot,
)


def test_care_recipient_model():
    p = PhysicianContact(name="Dr. Smith", specialty="Cardiology")
    v = DoctorVisit(
        physician_name="Dr. Smith", specialty="Cardiology", physician_findings="Blood pressure well managed."
    )
    m = MedicationSchedule(name="Lisinopril", dosage="10mg", timing_slot=TimingSlot.MORNING)
    vit = DailyVitalsLog(systolic_bp=125, diastolic_bp=80, heart_rate=68, spo2_pct=98.0)

    recipient = CareRecipient(
        full_name="Eleanor Vance",
        relationship="Mother",
        year_of_birth=1948,
        primary_diagnoses=["Hypertension", "Atrial Fibrillation"],
        physicians=[p],
        doctor_visits=[v],
        medications=[m],
        vitals_history=[vit],
    )

    d = recipient.to_dict()
    assert d["full_name"] == "Eleanor Vance"
    assert len(d["physicians"]) == 1
    assert len(d["doctor_visits"]) == 1
    assert len(d["medications"]) == 1
    assert len(d["vitals_history"]) == 1
