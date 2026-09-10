# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for medication and supplement interaction safety engine.
"""

from medcadence.interactions import InteractionSafetyEngine
from medcadence.models import InteractionSeverity, MedicationItem


def test_statin_grapefruit_interaction():
    med1 = MedicationItem(name="Atorvastatin", dosage="20mg")
    med2 = MedicationItem(name="Grapefruit Juice", is_supplement=True)

    alerts = InteractionSafetyEngine.audit_items([med1, med2])
    assert len(alerts) == 1
    assert alerts[0].severity == InteractionSeverity.SEVERE
    assert "CYP3A4" in alerts[0].mechanism


def test_ssri_5htp_contraindication():
    med1 = MedicationItem(name="Lexapro", dosage="10mg")
    med2 = MedicationItem(name="5-HTP", dosage="100mg", is_supplement=True)

    alerts = InteractionSafetyEngine.audit_items([med1, med2])
    assert len(alerts) == 1
    assert alerts[0].severity == InteractionSeverity.CONTRAINDICATED
    assert "Serotonin Syndrome" in alerts[0].mechanism


def test_iron_calcium_spacing_warning():
    med1 = MedicationItem(name="Ferrous Sulfate", dosage="65mg", is_supplement=True)
    med2 = MedicationItem(name="Calcium Carbonate", dosage="500mg", is_supplement=True)

    alerts = InteractionSafetyEngine.audit_items([med1, med2])
    assert len(alerts) == 1
    assert alerts[0].severity == InteractionSeverity.MILD_CAUTION


def test_safe_regimen_no_alerts():
    med1 = MedicationItem(name="Vitamin D3", dosage="2000IU", is_supplement=True)
    med2 = MedicationItem(name="Fish Oil", dosage="1000mg", is_supplement=True)

    alerts = InteractionSafetyEngine.audit_items([med1, med2])
    assert len(alerts) == 0
