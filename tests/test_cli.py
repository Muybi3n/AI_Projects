"""End-to-end integration tests for ShelfWise CLI subcommands."""

import json
from pathlib import Path

from shelfwise.cli import main


def test_cli_help_and_init(tmp_path: Path, capsys):
    # Empty args
    ret = main([])
    assert ret == 0
    out = capsys.readouterr().out
    assert "usage: shelfwise" in out

    # Init
    ret = main(["--data-dir", str(tmp_path), "init"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "ShelfWise initialized at" in out

    # Init JSON
    ret = main(["--data-dir", str(tmp_path), "--json", "init"])
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["status"] == "ready"


def test_cli_add_list_show(tmp_path: Path, capsys):
    d_dir = str(tmp_path)

    # Add asset 1
    ret = main(
        [
            "--data-dir",
            d_dir,
            "--ref-date",
            "2025-01-01",
            "add",
            "--name",
            "Dell PowerEdge T30",
            "--id",
            "srv-dell-t30",
            "--category",
            "homelab",
            "--brand",
            "Dell",
            "--model",
            "T30",
            "--serial",
            "4XYZ999",
            "--price",
            "499.00",
            "--purchase-date",
            "2024-01-10",
            "--vendor",
            "Dell Outlet",
            "--location",
            "Homelab Rack",
            "--status",
            "active",
            "--warranty-months",
            "12",
            "--tags",
            "server,virtualization",
            "--notes",
            "Primary hypervisor",
        ]
    )
    assert ret == 0
    out = capsys.readouterr().out
    assert "Added asset 'Dell PowerEdge T30'" in out
    assert "srv-dell-t30" in out

    # Add asset 2 with JSON
    ret = main(
        [
            "--data-dir",
            d_dir,
            "--json",
            "add",
            "--name",
            "Keychron Q1 Keyboard",
            "--category",
            "peripherals",
            "--price",
            "190.00",
            "--warranty-months",
            "24",
        ]
    )
    assert ret == 0
    out = capsys.readouterr().out
    added = json.loads(out)
    assert added["name"] == "Keychron Q1 Keyboard"
    assert added["category"] == "peripherals"

    # List
    ret = main(["--data-dir", d_dir, "list"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Dell PowerEdge T30" in out
    assert "Keychron Q1 Keyboard" in out

    # List with filter & JSON
    ret = main(["--data-dir", d_dir, "--json", "list", "--category", "homelab"])
    assert ret == 0
    out = capsys.readouterr().out
    items = json.loads(out)
    assert len(items) == 1
    assert items[0]["id"] == "srv-dell-t30"

    # Show
    ret = main(["--data-dir", d_dir, "show", "srv-dell-t30"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Dell PowerEdge T30" in out
    assert "Warranty Radar" in out

    # Show JSON
    ret = main(["--data-dir", d_dir, "--json", "show", "srv-dell-t30"])
    assert ret == 0
    out = capsys.readouterr().out
    show_data = json.loads(out)
    assert show_data["asset"]["id"] == "srv-dell-t30"
    assert "warranty" in show_data
    assert "depreciation" in show_data

    # Show non-existent
    ret = main(["--data-dir", d_dir, "show", "missing-id"])
    assert ret == 1


def test_cli_update_and_warranty(tmp_path: Path, capsys):
    d_dir = str(tmp_path)
    main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "ThinkPad X1 Carbon",
            "--id",
            "laptop-x1",
            "--price",
            "1400.00",
            "--purchase-date",
            "2024-12-25",
            "--warranty-months",
            "12",
        ]
    )
    capsys.readouterr()

    # Update
    ret = main(
        [
            "--data-dir",
            d_dir,
            "update",
            "laptop-x1",
            "--price",
            "1350.00",
            "--location",
            "Mobile Bag",
        ]
    )
    assert ret == 0
    out = capsys.readouterr().out
    assert "Updated asset" in out

    # Verify update in show
    main(["--data-dir", d_dir, "--json", "show", "laptop-x1"])
    show_d = json.loads(capsys.readouterr().out)
    assert show_d["asset"]["purchase_price"] == 1350.00
    assert show_d["asset"]["location"] == "Mobile Bag"

    # Update non-existent
    ret = main(["--data-dir", d_dir, "update", "missing-id", "--price", "100.0"])
    assert ret == 1

    # Warranty radar
    ret = main(
        [
            "--data-dir",
            d_dir,
            "--ref-date",
            "2025-01-01",
            "warranty",
        ]
    )
    assert ret == 0
    out = capsys.readouterr().out
    assert "Warranty Radar" in out
    assert "laptop-x1" in out

    # Warranty radar JSON with tier filter
    ret = main(
        [
            "--data-dir",
            d_dir,
            "--ref-date",
            "2025-01-01",
            "--json",
            "warranty",
            "--tier",
            "active",
        ]
    )
    assert ret == 0
    w_items = json.loads(capsys.readouterr().out)
    assert len(w_items) >= 1
    assert w_items[0]["evaluation"]["tier"] == "active"


def test_cli_maintenance_and_audit(tmp_path: Path, capsys):
    d_dir = str(tmp_path)
    main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "Custom Desktop",
            "--id",
            "pc-custom",
            "--price",
            "1800.00",
            "--purchase-date",
            "2023-01-01",
            "--warranty-months",
            "12",
        ]
    )
    capsys.readouterr()

    # Log maintenance
    ret = main(
        [
            "--data-dir",
            d_dir,
            "log-maintenance",
            "--asset-id",
            "pc-custom",
            "--type",
            "repair",
            "--date",
            "2024-05-10",
            "--cost",
            "120.00",
            "--desc",
            "Replaced power supply unit",
            "--performed-by",
            "Self",
            "--rma-ticket",
            "EVGA-RMA-888",
        ]
    )
    assert ret == 0
    out = capsys.readouterr().out
    assert "Logged maintenance event" in out

    # Log maintenance non-existent asset
    ret = main(["--data-dir", d_dir, "log-maintenance", "--asset-id", "no-such-asset"])
    assert ret == 1

    # Maintenance history
    ret = main(["--data-dir", d_dir, "maintenance-history"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Replaced power supply unit" in out

    # Maintenance history JSON
    ret = main(["--data-dir", d_dir, "--json", "maintenance-history", "--asset-id", "pc-custom"])
    assert ret == 0
    m_list = json.loads(capsys.readouterr().out)
    assert len(m_list) == 1
    assert m_list[0]["cost"] == 120.00

    # Audit
    ret = main(["--data-dir", d_dir, "audit"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Fleet Inventory Audit" in out
    assert "Total Acquisition Cost" in out

    # Audit JSON
    ret = main(["--data-dir", d_dir, "--json", "audit"])
    assert ret == 0
    audit_data = json.loads(capsys.readouterr().out)
    assert audit_data["total_assets"] >= 1
    assert audit_data["total_maintenance_spend"] == 120.00


def test_cli_receipts_and_claim_pack(tmp_path: Path, capsys):
    d_dir = str(tmp_path)
    rec_file = tmp_path / "camera_receipt.pdf"
    rec_file.write_text("OFFICIAL RECEIPT 777")

    main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "Sony A7 IV Camera",
            "--id",
            "cam-sony-a7",
            "--price",
            "2498.00",
            "--purchase-date",
            "2024-01-01",
            "--receipt",
            str(rec_file),
        ]
    )
    main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "Unreceipted Tablet",
            "--id",
            "tab-unrec",
            "--price",
            "600.00",
            "--purchase-date",
            "2024-02-01",
        ]
    )
    capsys.readouterr()

    # Receipts check
    ret = main(["--data-dir", d_dir, "receipts"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Receipt & Proof-of-Purchase Registry" in out
    assert "cam-sony-a7" in out

    # Receipts missing-only JSON
    ret = main(["--data-dir", d_dir, "--json", "receipts", "--missing-only"])
    assert ret == 0
    missing = json.loads(capsys.readouterr().out)
    assert any(m["asset_id"] == "tab-unrec" for m in missing)
    assert not any(m["asset_id"] == "cam-sony-a7" for m in missing)

    # Claim pack generation
    claim_out_file = tmp_path / "claim_dossier.md"
    ret = main(
        [
            "--data-dir",
            d_dir,
            "claim-pack",
            "--incident",
            "theft_or_loss",
            "--output",
            str(claim_out_file),
        ]
    )
    assert ret == 0
    assert claim_out_file.is_file()
    text = claim_out_file.read_text(encoding="utf-8")
    assert "INSURANCE & WARRANTY CLAIM PACK" in text
    assert "Sony A7 IV Camera" in text
    capsys.readouterr()

    # Claim pack JSON
    ret = main(
        [
            "--data-dir",
            d_dir,
            "--json",
            "claim-pack",
            "--asset-id",
            "cam-sony-a7",
        ]
    )
    assert ret == 0
    cp_json = json.loads(capsys.readouterr().out)
    assert len(cp_json["items"]) == 1
    assert cp_json["items"][0]["asset_id"] == "cam-sony-a7"


def test_cli_ask_and_export_delete(tmp_path: Path, capsys):
    d_dir = str(tmp_path)
    main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "Office Scanner",
            "--id",
            "scan-epson",
            "--price",
            "350.00",
        ]
    )
    capsys.readouterr()

    # Ask
    ret = main(["--data-dir", d_dir, "ask", "What is my warranty and replacement status?"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "ShelfWise Hardware Advisor" in out

    # Ask JSON
    ret = main(["--data-dir", d_dir, "--json", "ask", "Summarize fleet value"])
    assert ret == 0
    ask_res = json.loads(capsys.readouterr().out)
    assert "summary" in ask_res

    # Export CSV to file
    csv_file = tmp_path / "export.csv"
    ret = main(["--data-dir", d_dir, "export", "--format", "csv", "--output", str(csv_file)])
    assert ret == 0
    assert csv_file.is_file()
    assert "Office Scanner" in csv_file.read_text(encoding="utf-8")

    # Delete
    ret = main(["--data-dir", d_dir, "delete", "scan-epson", "--yes"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Deleted asset 'Office Scanner'" in out

    # Verify deleted
    ret = main(["--data-dir", d_dir, "show", "scan-epson"])
    assert ret == 1


def test_cli_comprehensive_coverage(tmp_path: Path, capsys):
    d_dir = str(tmp_path)
    rec_file = tmp_path / "doc.pdf"
    rec_file.write_text("TEST RECEIPT CONTENT")

    # Add item
    main(
        [
            "--data-dir",
            d_dir,
            "add",
            "--name",
            "Base Device",
            "--id",
            "base-dev",
            "--price",
            "100.00",
        ]
    )
    capsys.readouterr()

    # Full update hitting all fields
    ret = main(
        [
            "--data-dir",
            d_dir,
            "update",
            "base-dev",
            "--name",
            "Upgraded Device",
            "--category",
            "networking",
            "--brand",
            "Cisco",
            "--model",
            "SG300",
            "--serial",
            "SN-9876",
            "--purchase-date",
            "2024-03-01",
            "--vendor",
            "Newegg",
            "--condition",
            "refurbished",
            "--status",
            "rma",
            "--warranty-months",
            "36",
            "--ext-warranty-months",
            "12",
            "--ext-warranty-notes",
            "CarePack",
            "--receipt",
            str(rec_file),
            "--invoice",
            "INV-8888",
            "--tags",
            "switch,core",
            "--notes",
            "Rack 2 top",
        ]
    )
    assert ret == 0
    capsys.readouterr()

    # Show asset
    ret = main(["--data-dir", d_dir, "show", "base-dev"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Upgraded Device" in out
    assert "Cisco" in out
    assert "INV-8888" in out

    # Export stdout JSON & CSV
    ret = main(["--data-dir", d_dir, "export", "--format", "json"])
    assert ret == 0
    assert "Upgraded Device" in capsys.readouterr().out

    ret = main(["--data-dir", d_dir, "export", "--format", "csv"])
    assert ret == 0
    assert "Upgraded Device" in capsys.readouterr().out

    # Claim pack stdout (no output file)
    ret = main(["--data-dir", d_dir, "claim-pack"])
    assert ret == 0
    assert "INSURANCE & WARRANTY CLAIM PACK" in capsys.readouterr().out
