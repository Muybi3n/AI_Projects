# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for specialty profile storage.
"""

from pathlib import Path

from oncorenal.models import ChemoCycle
from oncorenal.storage import SpecialtyStore


def test_specialty_storage_crud(tmp_path: Path):
    store = SpecialtyStore(tmp_path)
    profile = store.load_profile()
    assert profile.patient_name == "Family Member"

    profile.patient_name = "Harold Miller"
    profile.chemo_cycles.append(ChemoCycle(regimen_name="Carboplatin", cycle_number=1))
    store.save_profile(profile)

    reloaded = store.load_profile()
    assert reloaded.patient_name == "Harold Miller"
    assert len(reloaded.chemo_cycles) == 1
    assert reloaded.chemo_cycles[0].regimen_name == "Carboplatin"
