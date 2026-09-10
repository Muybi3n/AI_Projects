# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for clinical jargon and acronym translation.
"""

from careguard.jargon import JargonTranslator


def test_decode_common_medical_acronyms():
    clinical_note = "78yo c/o SOB and DOE. Hx of CHF and HTN. Meds: Lasix 40mg po bid, prn nitroglycerin."
    decoded = JargonTranslator.decode_text(clinical_note)

    acronyms = [d.acronym for d in decoded]
    assert "SOB" in acronyms
    assert "CHF" in acronyms
    assert "HTN" in acronyms
    assert "BID" in acronyms
    assert "PRN" in acronyms
    assert "PO" in acronyms
