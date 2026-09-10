# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for onco-renal models and data structures.
"""

from oncorenal.models import (
    ChemoCycle,
    DialysisSession,
    FluidIntakeLog,
    OncoRenalProfile,
    SpecialtyLabRecord,
)


def test_oncorenal_profile_serialization():
    cycle = ChemoCycle(regimen_name="FOLFOX", cycle_number=1)
    session = DialysisSession(pre_dialysis_weight_kg=72.0, post_dialysis_weight_kg=69.5)
    fluid = FluidIntakeLog(fluid_intake_ml=850.0)
    lab = SpecialtyLabRecord(absolute_neutrophil_count_anc=1200.0, serum_potassium=4.8)

    profile = OncoRenalProfile(
        patient_name="Margaret Miller",
        primary_oncology_dx="Colorectal Cancer",
        primary_renal_dx="ESRD",
        chemo_cycles=[cycle],
        dialysis_sessions=[session],
        fluid_logs=[fluid],
        specialty_labs=[lab],
    )

    d = profile.to_dict()
    assert d["patient_name"] == "Margaret Miller"
    assert len(d["chemo_cycles"]) == 1
    assert len(d["dialysis_sessions"]) == 1
    assert len(d["fluid_logs"]) == 1
    assert len(d["specialty_labs"]) == 1
