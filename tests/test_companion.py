# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for AI Specialty Oncology & Renal Care Companion.
"""

from oncorenal.companion import SpecialtyCareCompanion, build_specialty_context
from oncorenal.models import ChemoCycle, OncoRenalProfile


def test_build_specialty_context():
    cycle = ChemoCycle(regimen_name="R-CHOP", cycle_number=2)
    profile = OncoRenalProfile(chemo_cycles=[cycle])

    ctx = build_specialty_context(profile)
    assert ctx["chemo_nadir_status"] is not None
    assert ctx["chemo_nadir_status"]["cycle_number"] == 2


def test_heuristic_companion_oncology_query():
    cycle = ChemoCycle(regimen_name="FOLFOX", cycle_number=1)
    profile = OncoRenalProfile(chemo_cycles=[cycle])

    companion = SpecialtyCareCompanion()
    resp = companion.consult("What should I watch out for during chemo nadir?", profile)

    assert len(resp.oncology_protocols) > 0
    assert len(resp.caregiver_specialty_checklist) > 0


def test_custom_llm_specialty_adapter():
    profile = OncoRenalProfile()

    def mock_llm(q: str, ctx: dict) -> str:
        return '{"clinical_summary": "Specialty guidance ready.", "caregiver_specialty_checklist": ["Check fistula bruit"]}'

    companion = SpecialtyCareCompanion(custom_llm_callable=mock_llm)
    resp = companion.consult("Dialysis guidance", profile)

    assert resp.clinical_summary == "Specialty guidance ready."
    assert "Check fistula bruit" in resp.caregiver_specialty_checklist
