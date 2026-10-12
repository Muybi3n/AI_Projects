"""Unit tests for ShelfWise local storage engine."""

import json
from pathlib import Path

from shelfwise.models import (
    Asset,
    AssetCategory,
    AssetStatus,
    MaintenanceRecord,
    MaintenanceType,
)
from shelfwise.storage import ShelfWiseStorage


def test_storage_asset_crud(tmp_path: Path):
    store = ShelfWiseStorage(data_dir=tmp_path)
    assert store.list_assets() == []

    asset = Asset(
        id="serv-01",
        name="Homelab Server",
        category=AssetCategory.HOMELAB,
        brand="Supermicro",
        purchase_price=850.0,
        location="Basement",
        status=AssetStatus.ACTIVE,
    )
    store.save_asset(asset)

    retrieved = store.get_asset("serv-01")
    assert retrieved is not None
    assert retrieved.name == "Homelab Server"
    assert retrieved.purchase_price == 850.0

    # Update
    asset.purchase_price = 899.0
    store.save_asset(asset)
    updated = store.get_asset("serv-01")
    assert updated is not None
    assert updated.purchase_price == 899.0

    # Delete
    assert store.delete_asset("serv-01") is True
    assert store.get_asset("serv-01") is None
    assert store.delete_asset("serv-01") is False


def test_storage_asset_filtering(tmp_path: Path):
    store = ShelfWiseStorage(data_dir=tmp_path)
    store.save_asset(
        Asset(
            id="a1", name="Dev Laptop", category=AssetCategory.COMPUTING, status=AssetStatus.ACTIVE, location="Office"
        )
    )
    store.save_asset(
        Asset(
            id="a2", name="Core Switch", category=AssetCategory.NETWORKING, status=AssetStatus.ACTIVE, location="Rack"
        )
    )
    store.save_asset(
        Asset(
            id="a3",
            name="Spare Switch",
            category=AssetCategory.NETWORKING,
            status=AssetStatus.STORAGE,
            location="Closet",
        )
    )

    assert len(store.list_assets(category="networking")) == 2
    assert len(store.list_assets(category="computing")) == 1
    assert len(store.list_assets(status="storage")) == 1
    assert len(store.list_assets(location="Rack")) == 1


def test_storage_maintenance_crud(tmp_path: Path):
    store = ShelfWiseStorage(data_dir=tmp_path)
    m1 = MaintenanceRecord(
        id="m-01",
        asset_id="a1",
        date="2025-02-01",
        maintenance_type=MaintenanceType.BATTERY,
        cost=45.0,
        description="Replaced battery",
    )
    m2 = MaintenanceRecord(
        id="m-02",
        asset_id="a2",
        date="2025-03-01",
        maintenance_type=MaintenanceType.FIRMWARE,
        cost=0.0,
        description="Upgraded OS",
    )
    store.save_maintenance(m1)
    store.save_maintenance(m2)

    all_m = store.list_maintenance()
    assert len(all_m) == 2

    a1_m = store.list_maintenance(asset_id="a1")
    assert len(a1_m) == 1
    assert a1_m[0].id == "m-01"

    assert store.delete_maintenance("m-01") is True
    assert len(store.list_maintenance()) == 1


def test_storage_config_and_export_import(tmp_path: Path):
    store = ShelfWiseStorage(data_dir=tmp_path)
    store.save_config({"currency": "USD", "auto_hash": True})
    cfg = store.get_config()
    assert cfg["currency"] == "USD"
    assert cfg["auto_hash"] is True

    store.save_asset(Asset(id="a1", name="Router", purchase_price=120.0))
    store.save_maintenance(MaintenanceRecord(id="m1", asset_id="a1", date="2025-01-01", cost=15.0))

    # Export JSON
    json_out = store.export_data("json")
    parsed = json.loads(json_out)
    assert len(parsed["assets"]) == 1
    assert len(parsed["maintenance"]) == 1

    # Export CSV
    csv_out = store.export_data("csv")
    assert "Router" in csv_out
    assert "120.0" in csv_out

    # Import into fresh store
    store2 = ShelfWiseStorage(data_dir=tmp_path / "second_store")
    a_count, m_count = store2.import_data(parsed)
    assert a_count == 1
    assert m_count == 1
    assert store2.get_asset("a1") is not None
