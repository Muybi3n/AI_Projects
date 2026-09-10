# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for health models and biomarker classification.
"""

from medcadence.models import (
    BiomarkerCategory,
    BiomarkerRecord,
    BiomarkerStatus,
    HealthProfile,
    MedicationItem,
)


def test_biomarker_status_evaluation():
    # Normal LDL
    b1 = BiomarkerRecord(name="LDL", ref_low=0.0, ref_high=100.0, value=85.0)
    assert b1.status == BiomarkerStatus.OPTIMAL

    # Borderline High LDL
    b2 = BiomarkerRecord(name="LDL", ref_low=0.0, ref_high=100.0, value=115.0)
    assert b2.status == BiomarkerStatus.BORDERLINE_HIGH

    # Critically High LDL
    b3 = BiomarkerRecord(name="LDL", ref_low=0.0, ref_high=100.0, value=150.0)
    assert b3.status == BiomarkerStatus.CRITICALLY_HIGH

    # Low Fasting Glucose
    b4 = BiomarkerRecord(name="Glucose", ref_low=70.0, ref_high=99.0, value=50.0)
    assert b4.status == BiomarkerStatus.BORDERLINE_LOW


def test_health_profile_serialization():
    profile = HealthProfile(
        user_label="Test User",
        biomarkers=[BiomarkerRecord(name="HbA1c", category=BiomarkerCategory.METABOLIC_GLYCEMIC, value=5.4)],
        medications=[MedicationItem(name="Vitamin D3", dosage="2000IU", is_supplement=True)],
    )

    d = profile.to_dict()
    assert d["user_label"] == "Test User"
    assert len(d["biomarkers"]) == 1
    assert len(d["medications"]) == 1
