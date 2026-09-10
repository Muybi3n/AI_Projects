# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for HIPAA PHI de-identification and sensitive finding redaction.
"""

from careguard.deid import ClinicalRedactor


def test_deidentify_phi_identifiers():
    sample_text = """
    Patient: Arthur Dent, DOB: 05/12/1946, Phone: (555) 234-5678, SSN: 123-45-6789.
    Attending Physician: Dr. Sarah Chen at University Medical. Email: dr.chen@hospital.org.
    MRN: #MRN-987452.
    """

    res = ClinicalRedactor.deidentify(sample_text, patient_name_hint="Arthur Dent")

    assert "[PATIENT_NAME]" in res.sanitized_text
    assert "Arthur Dent" not in res.sanitized_text
    assert "[PHONE]" in res.sanitized_text
    assert "555" not in res.sanitized_text
    assert "[SSN]" in res.sanitized_text
    assert "[DOB_REDACTED]" in res.sanitized_text
    assert "[EMAIL]" in res.sanitized_text
    assert len(res.redacted_phi_items) >= 5


def test_redact_sensitive_lab_and_cancer_findings():
    sample_note = """
    Assessment: Patient with Stage IVb adenocarcinoma.
    Lab results: PSA: 14.2 ng/mL, WBC: 18.5, Creatinine: 2.1 mg/dL.
    Biopsy positive for invasive ductal carcinoma.
    """

    res = ClinicalRedactor.deidentify(sample_note, redact_sensitive_findings=True)

    # Verify sensitive numbers and staging terms are replaced with privacy tokens
    assert "14.2" not in res.sanitized_text
    assert "Stage IVb" not in res.sanitized_text
    assert "[LAB_VALUE_REDACTED]" in res.sanitized_text
    assert "[SENSITIVE_DIAGNOSTIC_REDACTED]" in res.sanitized_text
    assert len(res.redacted_sensitive_findings) >= 3
