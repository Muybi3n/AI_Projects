"""Full CLI workflow tests for nasroute-core."""

import json
from pathlib import Path

from nasroute.cli import format_bytes, main


def test_format_bytes():
    assert format_bytes(500) == "500.0 B"
    assert "KB" in format_bytes(2048)
    assert "MB" in format_bytes(1024 * 1024 * 5)
    assert "GB" in format_bytes(1024 * 1024 * 1024 * 10)


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "nas_data"
    inbox = tmp_path / "inbox"
    inbox.mkdir()

    # Create dummy sample documents
    f_tax = inbox / "2024_w2_irs_tax_statement.pdf"
    f_tax.write_text("Tax Return W-2 Form 2024", encoding="utf-8")

    f_rec = inbox / "hardware_receipt_2024_03.txt"
    f_rec.write_text("Home Depot invoice order purchase $150", encoding="utf-8")

    f_log = inbox / "syslog_audit_pcap.log"
    f_log.write_text("kernel auditd syslog stream", encoding="utf-8")

    # 1. Test init
    assert main(["--data-dir", str(data_dir), "init"]) == 0
    out = capsys.readouterr().out
    assert "Initialized NASRoute" in out

    # Test init JSON
    assert main(["--data-dir", str(data_dir), "init", "--json"]) == 0
    out_json = capsys.readouterr().out
    data_init = json.loads(out_json)
    assert data_init["status"] == "INITIALIZED"

    # 2. Test scan
    assert main(["--data-dir", str(data_dir), "scan", str(inbox)]) == 0
    out_scan = capsys.readouterr().out
    assert "2024_w2_irs_tax_statement.pdf" in out_scan
    assert "TAX_FINANCE" in out_scan

    # Test scan JSON
    assert main(["--data-dir", str(data_dir), "scan", str(inbox), "--json"]) == 0
    scan_json = json.loads(capsys.readouterr().out)
    assert scan_json["total_files"] == 3

    # 3. Test tiers list & add
    assert main(["--data-dir", str(data_dir), "tiers", "list"]) == 0
    out_tiers = capsys.readouterr().out
    assert "HOT_NVME" in out_tiers

    assert main(["--data-dir", str(data_dir), "tiers", "list", "--json"]) == 0
    tiers_json = json.loads(capsys.readouterr().out)
    assert "HOT_NVME" in tiers_json

    custom_mount = tmp_path / "custom_mount"
    custom_mount.mkdir()
    assert (
        main(
            [
                "--data-dir",
                str(data_dir),
                "tiers",
                "add",
                "--name",
                "NVME_FAST",
                "--mount",
                str(custom_mount),
                "--speed",
                "PCIe_4",
                "--capacity-gb",
                "500",
            ]
        )
        == 0
    )
    assert "Registered storage tier 'NVME_FAST'" in capsys.readouterr().out

    # 4. Test rules list, add, remove
    assert main(["--data-dir", str(data_dir), "rules", "list"]) == 0
    out_rules = capsys.readouterr().out
    assert "rule_taxes" in out_rules

    assert main(["--data-dir", str(data_dir), "rules", "list", "--json"]) == 0
    rules_json = json.loads(capsys.readouterr().out)
    assert len(rules_json) >= 7

    assert (
        main(
            [
                "--data-dir",
                str(data_dir),
                "rules",
                "add",
                "--id",
                "rule_docker_test",
                "--name",
                "Docker Configs",
                "--category",
                "HOMELAB_SYSADMIN",
                "--tier",
                "HOT_NVME",
                "--subpath",
                "Homelab/Docker/{year}/{filename}",
                "--keywords",
                "docker,compose",
                "--priority",
                "180",
            ]
        )
        == 0
    )
    assert "Added taxonomy rule" in capsys.readouterr().out

    assert main(["--data-dir", str(data_dir), "rules", "remove", "--id", "rule_docker_test"]) == 0
    assert "Removed taxonomy rule" in capsys.readouterr().out

    assert main(["--data-dir", str(data_dir), "rules", "remove", "--id", "rule_nonexistent"]) == 1
    capsys.readouterr()

    # 5. Test route dry-run
    assert main(["--data-dir", str(data_dir), "route", str(inbox), "--dry-run"]) == 0
    out_dry = capsys.readouterr().out
    assert "SIMULATED" in out_dry

    # Test route copy (real execution)
    assert main(["--data-dir", str(data_dir), "route", str(inbox), "--action", "copy"]) == 0
    out_route = capsys.readouterr().out
    assert "Routing Execution: COPY" in out_route
    assert "SUCCESS" in out_route

    # Test route json
    assert main(["--data-dir", str(data_dir), "route", str(inbox), "--action", "copy", "--json"]) == 0
    route_json = json.loads(capsys.readouterr().out)
    assert route_json["total_files_scanned"] == 3

    # 6. Test audit
    assert main(["--data-dir", str(data_dir), "audit"]) == 0
    out_audit = capsys.readouterr().out
    assert "NASRoute System Storage Audit" in out_audit

    assert main(["--data-dir", str(data_dir), "audit", "--json"]) == 0
    audit_json = json.loads(capsys.readouterr().out)
    assert audit_json["total_indexed_files"] > 0

    # 7. Test ask (AI companion)
    assert main(["--data-dir", str(data_dir), "ask", "How should I structure my cold storage tier?"]) == 0
    out_ask = capsys.readouterr().out
    assert "AI Storage Companion" in out_ask
    assert "COLD_NAS" in out_ask

    assert (
        main(
            [
                "--data-dir",
                str(data_dir),
                "ask",
                "Suggest taxonomy rules for IRS tax returns",
                "--json",
            ]
        )
        == 0
    )
    ask_json = json.loads(capsys.readouterr().out)
    assert "query" in ask_json
    assert len(ask_json["suggested_rules"]) > 0


def test_cli_error_paths(tmp_path: Path, capsys):
    data_dir = tmp_path / "nas_data"

    # Scan nonexistent path
    assert main(["--data-dir", str(data_dir), "scan", str(tmp_path / "nonexistent")]) == 1
    capsys.readouterr()

    # Route nonexistent source
    assert main(["--data-dir", str(data_dir), "route", str(tmp_path / "nonexistent")]) == 1
    capsys.readouterr()

    # No command
    assert main(["--data-dir", str(data_dir)]) == 0
    capsys.readouterr()
