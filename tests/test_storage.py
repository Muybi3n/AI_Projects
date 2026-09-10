# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Tests for local snapshot storage and historical tracking.
"""

from pathlib import Path

from capdrift.models import Holding, PortfolioSnapshot
from capdrift.storage import SnapshotStore


def test_snapshot_storage_crud(tmp_path: Path):
    store = SnapshotStore(tmp_path)

    h = Holding(symbol="VOO", name="S&P 500", shares=10.0, current_price=500.0)
    snap = PortfolioSnapshot(id="snap_1", cash_balance=1000.0, holdings=[h])

    store.save_snapshot(snap)
    snaps = store.list_snapshots()

    assert len(snaps) == 1
    assert snaps[0].id == "snap_1"
    assert snaps[0].total_equity == 6000.0

    latest = store.get_latest_snapshot()
    assert latest is not None
    assert latest.id == "snap_1"
