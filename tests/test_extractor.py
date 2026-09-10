# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for structured clinical point extraction.
"""

from careguard.extractor import NoteExtractor


def test_extract_from_unstructured_note():
    note = """
    Chief Complaint: Increasing fatigue and bilateral leg edema.
    Assessment:
    • Worsening congestive heart failure (CHF)
    • Uncontrolled hypertension (HTN)
    Medication Changes:
    • Increase Furosemide to 40mg po bid
    • Hold Lisinopril
    Plan:
    • Order 2D Echocardiogram
    • Repeat BMP in 2 weeks
    """

    extracted = NoteExtractor.extract_from_note(note, encounter_date="2026-09-10", patient_name_hint="John Doe")

    assert "fatigue" in extracted.chief_complaint.lower()
    assert len(extracted.diagnoses_and_assessments) >= 2
    assert len(extracted.medication_changes) >= 2
    assert len(extracted.follow_up_orders_and_labs) >= 2
    assert len(extracted.decoded_jargon) >= 2
    assert extracted.encounter_date == "2026-09-10"
