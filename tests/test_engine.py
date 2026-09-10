# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for vitals anomaly detection, pillbox schedule, and physician visit prep sheets.
"""

from careguard.engine import CareEngine
from careguard.models import (
    CareRecipient,
    DailyVitalsLog,
    MedicationSchedule,
    TimingSlot,
)


def test_vitals_anomaly_detection():
    # Hypertensive crisis + low oxygen
    v1 = DailyVitalsLog(systolic_bp=190, diastolic_bp=125, spo2_pct=89.0)
    # Rapid weight gain
    v2 = DailyVitalsLog(weight_lbs=140.0)
    v3 = DailyVitalsLog(weight_lbs=144.5)  # +4.5 lbs gain

    recipient = CareRecipient(vitals_history=[v1, v2, v3])
    anomalies = CareEngine.audit_vitals(recipient)

    assert len(anomalies) >= 3
    metrics = [a.vital_metric for a in anomalies]
    assert "Blood Pressure" in metrics
    assert "Oxygen Saturation (SpO2)" in metrics
    assert "Weight Gain (Fluid Retention)" in metrics


def test_pillbox_schedule_grouping():
    m1 = MedicationSchedule(name="Metformin", dosage="500mg", timing_slot=TimingSlot.MORNING)
    m2 = MedicationSchedule(name="Atorvastatin", dosage="20mg", timing_slot=TimingSlot.BEDTIME)

    recipient = CareRecipient(medications=[m1, m2])
    pillbox = CareEngine.get_pillbox_schedule(recipient)

    assert len(pillbox["morning"]) == 1
    assert pillbox["morning"][0]["name"] == "Metformin"
    assert len(pillbox["bedtime"]) == 1


def test_generate_physician_briefing():
    v = DailyVitalsLog(systolic_bp=130, diastolic_bp=82, heart_rate=72, spo2_pct=97.5)
    recipient = CareRecipient(
        full_name="Arthur Pendelton",
        relationship="Father",
        year_of_birth=1945,
        primary_diagnoses=["Congestive Heart Failure"],
        vitals_history=[v],
    )

    brief = CareEngine.generate_physician_briefing(recipient)
    assert brief.patient_name == "Arthur Pendelton"
    assert brief.age == 2026 - 1945
    assert len(brief.recommended_discussion_points) > 0
