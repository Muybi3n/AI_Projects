"""Edge case tests for ShelfWise."""

from pathlib import Path
from unittest.mock import patch

from shelfwise.cli import main, slugify
from shelfwise.engine import calculate_warranty
from shelfwise.models import Asset, WarrantyTier
from shelfwise.storage import ShelfWiseStorage


def test_slugify():
    assert slugify("Mac Mini M2!") == "mac-mini-m2"
    assert slugify("   Dell PowerEdge T30 --- ") == "dell-poweredge-t30"
    assert slugify("Sony @#$ A7-IV") == "sony-a7-iv"


def test_storage_corrupted_json(tmp_path: Path):
    store = ShelfWiseStorage(data_dir=tmp_path)
    # Write garbage to assets.json
    store.assets_file.write_text("CORRUPTED_NOT_JSON!!!", encoding="utf-8")
    assert store.list_assets() == []

    # Write garbage to maintenance.json
    store.maintenance_file.write_text("{malformed: json", encoding="utf-8")
    assert store.list_maintenance() == []


def test_slug_collision_and_auto_generation(tmp_path: Path):
    d_dir = str(tmp_path)
    # First item without ID
    ret1 = main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "Raspberry Pi 5",
            "--brand",
            "Raspberry Pi",
        ]
    )
    assert ret1 == 0

    # Second item with same name/brand without ID
    ret2 = main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "Raspberry Pi 5",
            "--brand",
            "Raspberry Pi",
        ]
    )
    assert ret2 == 0

    store = ShelfWiseStorage(data_dir=tmp_path)
    assets = store.list_assets()
    assert len(assets) == 2
    assert assets[0].id != assets[1].id


def test_warranty_empty_or_invalid_purchase_date():
    a_empty = Asset(id="e1", name="No Date Device", purchase_date="")
    eval_empty = calculate_warranty(a_empty)
    assert eval_empty.tier == WarrantyTier.EXPIRED

    a_bad = Asset(id="b1", name="Bad Date Device", purchase_date="NOT-A-DATE")
    eval_bad = calculate_warranty(a_bad)
    assert eval_bad.tier == WarrantyTier.EXPIRED


def test_delete_prompt_cancellation(tmp_path: Path, capsys):
    d_dir = str(tmp_path)
    main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "Important Server",
            "--id",
            "srv-keep",
        ]
    )
    capsys.readouterr()

    # User enters "n" to cancel deletion
    with patch("builtins.input", return_value="n"):
        ret = main(["--data-dir", d_dir, "delete", "srv-keep"])
        assert ret == 0
        out = capsys.readouterr().out
        assert "Deletion cancelled" in out

    # Asset should still exist
    store = ShelfWiseStorage(data_dir=tmp_path)
    assert store.get_asset("srv-keep") is not None
