# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for local trust storage management.
"""

from pathlib import Path

from trustguard.models import ScheduleAsset
from trustguard.storage import TrustStore


def test_trust_storage_save_and_load(tmp_path: Path):
    store = TrustStore(tmp_path)
    trust = store.load_trust()
    assert trust.trust_name == "Primary Family Revocable Living Trust"

    trust.trust_name = "Modified Trust"
    trust.assets.append(ScheduleAsset(name="New Asset", estimated_value=250000.0))
    store.save_trust(trust)

    reloaded = store.load_trust()
    assert reloaded.trust_name == "Modified Trust"
    assert len(reloaded.assets) == 1
    assert reloaded.assets[0].estimated_value == 250000.0
