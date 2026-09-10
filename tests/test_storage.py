# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for PtoStore.
"""

from pathlib import Path

from ptomax.models import WorkCoverage
from ptomax.storage import PtoStore


def test_pto_storage_crud(tmp_path: Path):
    store = PtoStore(tmp_path)
    profile = store.load_profile()
    assert profile.current_balance_days == 15.0

    profile.current_balance_days = 18.0
    profile.coverage_handovers.append(
        WorkCoverage(
            id="cov-99",
            project_or_domain="Test Project",
            primary_cover_name="Bob",
            primary_cover_contact="bob@corp.local",
        )
    )
    store.save_profile(profile)

    reloaded = store.load_profile()
    assert reloaded.current_balance_days == 18.0
    assert any(c.id == "cov-99" for c in reloaded.coverage_handovers)
