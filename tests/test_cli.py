"""Tests for CLI entry points."""

import json
from pathlib import Path

import pytest

from drivemesh.cli import format_bytes, main
from drivemesh.importer import DriveImporter


def test_format_bytes():
    assert format_bytes(500) == "500 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.00 MB"
    assert format_bytes(3 * 1024 * 1024 * 1024) == "3.00 GB"


def test_cli_demo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    db_file = str(tmp_path / "demo.db")
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "demo"])
    main()
    captured = capsys.readouterr()
    assert "Initializing DriveMesh Demo Mode" in captured.out
    assert "DEMO RUN: DRIVE HEALTH & STORAGE AUDIT" in captured.out


def test_cli_empty_db_guards(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    empty_db = str(tmp_path / "empty.db")
    # cluster empty
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", empty_db, "cluster"])
    main()
    captured = capsys.readouterr()
    assert "No files indexed yet" in captured.out

    # duplicates empty
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", empty_db, "duplicates"])
    main()
    captured = capsys.readouterr()
    assert "No files indexed yet" in captured.out

    # plan empty
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", empty_db, "plan"])
    main()
    captured = capsys.readouterr()
    assert "No files indexed yet" in captured.out


def test_cli_scan_cluster_duplicates_audit_plan_ask_search(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    db_file = str(tmp_path / "cli_test.db")
    export_json = tmp_path / "export.json"
    demo_files = DriveImporter.generate_demo_dataset()
    export_json.write_text(json.dumps([f.to_dict() for f in demo_files]), encoding="utf-8")

    # 1. scan
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "scan", str(export_json)])
    main()
    captured = capsys.readouterr()
    assert "Ingestion complete" in captured.out

    # 2. cluster
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "cluster"])
    main()
    captured = capsys.readouterr()
    assert "DISCOVERED SUBJECT CLUSTERS" in captured.out

    # 3. duplicates with filter
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "duplicates", "--type", "exact_checksum"])
    main()
    captured = capsys.readouterr()
    assert "DUPLICATE AUDIT REPORT" in captured.out

    # 4. audit
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "audit"])
    main()
    captured = capsys.readouterr()
    assert "GOOGLE DRIVE / CLOUD STORAGE HEALTH" in captured.out

    # 5. audit json
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "audit", "--json"])
    main()
    captured = capsys.readouterr()
    parsed_json = json.loads(captured.out)
    assert "health_score" in parsed_json

    # 6. plan stdout
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "plan"])
    main()
    captured = capsys.readouterr()
    assert "DRIVE RESTRUCTURING PLAN" in captured.out

    # 6b. plan to file
    plan_out = str(tmp_path / "plan.json")
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "plan", "--out", plan_out])
    main()
    captured = capsys.readouterr()
    assert "saved to" in captured.out

    # 7. search
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "search", "tax"])
    main()
    captured = capsys.readouterr()
    assert "Search Results for 'tax'" in captured.out

    # 8. ask
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "ask", "How can I clean duplicates?"])
    main()
    captured = capsys.readouterr()
    assert "Duplicate Resolution Advisory" in captured.out


def test_cli_scan_csv_and_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    db_file = str(tmp_path / "scan_formats.db")

    # CSV scan
    csv_file = tmp_path / "input.csv"
    csv_file.write_text("id,name,size_bytes\nf1,Test.pdf,1024\n", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "scan", str(csv_file)])
    main()
    captured = capsys.readouterr()
    assert "Ingestion complete" in captured.out

    # Directory scan
    sub_dir = tmp_path / "scan_dir"
    sub_dir.mkdir()
    (sub_dir / "sample.txt").write_text("sample content", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["drivemesh", "--db", db_file, "scan", str(sub_dir)])
    main()
    captured = capsys.readouterr()
    assert "Ingestion complete" in captured.out
