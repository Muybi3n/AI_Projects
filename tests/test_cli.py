"""End-to-end integration tests for subwatch CLI commands."""

import json
from pathlib import Path

from subwatch.cli import main


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = str(tmp_path / "subwatch_data")

    # 1. Add subscription
    exit_code = main(
        [
            "--data-dir",
            data_dir,
            "add",
            "--name",
            "Netflix Premium",
            "--price",
            "22.99",
            "--category",
            "entertainment",
            "--cycle",
            "monthly",
            "--renewal-date",
            "2026-10-20",
            "--usage",
            "4",
            "--payment-method",
            "Chase Sapphire ...4321",
        ]
    )
    assert exit_code == 0

    # Try duplicate add
    exit_code_dup = main(
        [
            "--data-dir",
            data_dir,
            "add",
            "--name",
            "Netflix Premium",
            "--price",
            "22.99",
        ]
    )
    assert exit_code_dup == 1

    # Add second subscription (with explicit start date and initial charge)
    main(
        [
            "--data-dir",
            data_dir,
            "add",
            "--name",
            "GitHub Copilot",
            "--price",
            "10.00",
            "--category",
            "developer_cloud",
            "--cycle",
            "monthly",
            "--start-date",
            "2025-01-01",
            "--initial-charge",
            "10.00",
            "--usage",
            "5",
        ]
    )

    # Add third subscription (zombie)
    main(
        [
            "--data-dir",
            data_dir,
            "add",
            "--name",
            "Old Gym Membership",
            "--price",
            "49.00",
            "--category",
            "health_fitness",
            "--cycle",
            "monthly",
            "--usage",
            "1",
        ]
    )

    # 2. List
    exit_code = main(["--data-dir", data_dir, "list"])
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "Netflix Premium" in out
    assert "GitHub Copilot" in out

    # List with filter
    exit_code = main(
        [
            "--data-dir",
            data_dir,
            "list",
            "--status",
            "active",
            "--category",
            "entertainment",
        ]
    )
    assert exit_code == 0
    out_filtered, _ = capsys.readouterr()
    assert "Netflix Premium" in out_filtered

    # List with JSON
    exit_code = main(["--data-dir", data_dir, "list", "--json"])
    assert exit_code == 0
    out_json, _ = capsys.readouterr()
    parsed = json.loads(out_json)
    assert len(parsed) == 3

    # 3. Log Charge & Detect Price Creep
    exit_code = main(
        [
            "--data-dir",
            data_dir,
            "log-charge",
            "GitHub Copilot",
            "--amount",
            "14.00",
            "--date",
            "2026-10-01",
            "--notes",
            "Annual price adjustment",
        ]
    )
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "STEALTH PRICE CREEP DETECTED" in out

    # 4. Update
    exit_code = main(
        [
            "--data-dir",
            data_dir,
            "update",
            "Netflix Premium",
            "--price",
            "24.99",
            "--status",
            "active",
            "--cycle",
            "monthly",
            "--category",
            "entertainment",
            "--renewal-date",
            "2026-11-20",
            "--usage",
            "3",
            "--notes",
            "Review before next season",
        ]
    )
    assert exit_code == 0

    # 5. Audit
    exit_code = main(["--data-dir", data_dir, "audit"])
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "SUBWATCH COMPREHENSIVE SUBSCRIPTION" in out
    assert "Price Creep & Stealth Inflation Alerts" in out
    assert "Low-Usage & Zombie Subscriptions" in out

    # Audit JSON
    exit_code = main(["--data-dir", data_dir, "audit", "--json"])
    assert exit_code == 0
    out_json, _ = capsys.readouterr()
    audit_data = json.loads(out_json)
    assert audit_data["total_active_subscriptions"] == 3

    # 6. Renewals
    exit_code = main(["--data-dir", data_dir, "renewals", "--days", "60"])
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "Upcoming Renewal Radar" in out

    # 7. Brief
    exit_code = main(["--data-dir", data_dir, "brief", "GitHub Copilot"])
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "Cancellation Playbook: GitHub Copilot" in out

    exit_code = main(["--data-dir", data_dir, "brief", "GitHub Copilot", "--negotiate"])
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "Retention Negotiation Script: GitHub Copilot" in out

    # 8. Ask
    exit_code = main(["--data-dir", data_dir, "ask", "How", "can", "I", "save", "money?"])
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "Subscription Cost Optimization" in out

    # 9. Ingest CSV
    csv_file = tmp_path / "statement.csv"
    csv_file.write_text(
        "Date,Merchant,Amount\n2026-09-10,SPOTIFY USA,$10.99\n2026-09-11,CLOUDFLARE INC,$20.00\n",
        encoding="utf-8",
    )
    # Preview ingest without auto-add
    exit_code = main(["--data-dir", data_dir, "ingest", "--file", str(csv_file)])
    assert exit_code == 0
    out_ingest, _ = capsys.readouterr()
    assert "Detected 2 Recurring Candidate Transactions" in out_ingest

    # Ingest with auto-add
    exit_code = main(
        [
            "--data-dir",
            data_dir,
            "ingest",
            "--file",
            str(csv_file),
            "--auto-add",
        ]
    )
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "Automatically imported" in out

    # 10. Export
    export_json = tmp_path / "export.json"
    exit_code = main(
        [
            "--data-dir",
            data_dir,
            "export",
            "--format",
            "json",
            "--out",
            str(export_json),
        ]
    )
    assert exit_code == 0
    assert export_json.exists()

    export_md = tmp_path / "export.md"
    exit_code = main(
        [
            "--data-dir",
            data_dir,
            "export",
            "--format",
            "md",
            "--out",
            str(export_md),
        ]
    )
    assert exit_code == 0
    assert export_md.exists()

    # stdout export
    exit_code = main(["--data-dir", data_dir, "export", "--format", "json"])
    assert exit_code == 0
    out_exp, _ = capsys.readouterr()
    assert "summary" in out_exp

    # 11. Remove
    exit_code = main(["--data-dir", data_dir, "remove", "Old Gym Membership"])
    assert exit_code == 0
    out, _ = capsys.readouterr()
    assert "Removed subscription" in out


def test_cli_errors_and_edge_cases(tmp_path: Path, capsys):
    data_dir = str(tmp_path / "subwatch_empty")

    # Empty list
    main(["--data-dir", data_dir, "list"])
    out, _ = capsys.readouterr()
    assert "No subscriptions found" in out

    # Empty renewals
    main(["--data-dir", data_dir, "renewals"])
    out_ren, _ = capsys.readouterr()
    assert "No subscriptions renewing" in out_ren

    # Log charge on non-existing
    exit_code = main(["--data-dir", data_dir, "log-charge", "ghost", "--amount", "10.0"])
    assert exit_code == 1

    # Update non-existing
    exit_code = main(["--data-dir", data_dir, "update", "ghost", "--price", "20.0"])
    assert exit_code == 1

    # Remove non-existing
    exit_code = main(["--data-dir", data_dir, "remove", "ghost"])
    assert exit_code == 1

    # Brief non-existing
    exit_code = main(["--data-dir", data_dir, "brief", "ghost"])
    assert exit_code == 1

    # Ingest missing file
    exit_code = main(["--data-dir", data_dir, "ingest", "--file", "nonexistent.csv"])
    assert exit_code == 1

    # Ingest empty CSV
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("", encoding="utf-8")
    exit_code = main(["--data-dir", data_dir, "ingest", "--file", str(empty_csv)])
    assert exit_code == 0
    out_empty, _ = capsys.readouterr()
    assert "No recurring subscription patterns detected" in out_empty

    # Ask empty
    exit_code = main(["--data-dir", data_dir, "ask", "   "])
    assert exit_code == 1

    # No arguments
    exit_code = main([])
    assert exit_code == 1
