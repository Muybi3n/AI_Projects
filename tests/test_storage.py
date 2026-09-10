# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for care recipient storage.
"""

from pathlib import Path

from careguard.models import MedicationSchedule
from careguard.storage import CareStore


def test_care_storage_crud(tmp_path: Path):
    store = CareStore(tmp_path)
    recipient = store.load_recipient()
    assert recipient.full_name == "Family Member"

    recipient.full_name = "Margaret Miller"
    recipient.medications.append(MedicationSchedule(name="Metoprolol", dosage="25mg"))
    store.save_recipient(recipient)

    reloaded = store.load_recipient()
    assert reloaded.full_name == "Margaret Miller"
    assert len(reloaded.medications) == 1
    assert reloaded.medications[0].name == "Metoprolol"
