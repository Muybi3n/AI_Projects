# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for health storage management.
"""

from pathlib import Path

from medcadence.models import BiomarkerRecord
from medcadence.storage import HealthStore


def test_health_storage_crud(tmp_path: Path):
    store = HealthStore(tmp_path)
    profile = store.load_profile()
    assert profile.user_label == "Primary User"

    profile.biomarkers.append(BiomarkerRecord(name="HbA1c", value=5.2))
    store.save_profile(profile)

    reloaded = store.load_profile()
    assert len(reloaded.biomarkers) == 1
    assert reloaded.biomarkers[0].name == "HbA1c"
