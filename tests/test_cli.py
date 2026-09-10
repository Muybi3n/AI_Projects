# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive CLI integration and edge case tests.
"""

import json
from pathlib import Path

from sparsededup.cli import main, parse_size, print_banner


def test_parse_size_valid_and_invalid():
    assert parse_size("100") == 100
    assert parse_size("100B") == 100
    assert parse_size("10KB") == 10 * 1024
    assert parse_size("5MB") == 5 * 1024 * 1024
    assert parse_size("1.5GB") == int(1.5 * 1024 * 1024 * 1024)
    assert parse_size("1TB") == 1024**4
    assert parse_size("1PB") == 1024**5
    assert parse_size("1EB") == 1024**6

    try:
        parse_size("invalid-size")
        assert False, "Should raise ValueError"
    except ValueError:
        pass


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "sparsededup" in captured.out


def test_cli_dry_run(tmp_path: Path, capsys):
    f1 = tmp_path / "a.dat"
    f2 = tmp_path / "b.dat"
    f1.write_bytes(b"CLI test data 12345")
    f2.write_bytes(b"CLI test data 12345")

    exit_code = main([str(tmp_path), "--dry-run", "--quiet"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Redundant Duplicate Files: 1" in captured.out


def test_cli_json_output(tmp_path: Path, capsys):
    f1 = tmp_path / "a.dat"
    f2 = tmp_path / "b.dat"
    f1.write_bytes(b"CLI test data 12345")
    f2.write_bytes(b"CLI test data 12345")

    exit_code = main([str(tmp_path), "--json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["summary"]["duplicate_files"] == 1


def test_cli_json_out_file(tmp_path: Path, capsys):
    f1 = tmp_path / "a.dat"
    f2 = tmp_path / "b.dat"
    manifest = tmp_path / "out.json"
    f1.write_bytes(b"Manifest export test")
    f2.write_bytes(b"Manifest export test")

    exit_code = main([str(tmp_path), "--json-out", str(manifest), "--quiet"])
    assert exit_code == 0
    assert manifest.exists()


def test_cli_hardlink_with_confirm(tmp_path: Path, capsys):
    f1 = tmp_path / "a.dat"
    f2 = tmp_path / "b.dat"
    f1.write_bytes(b"CLI hardlink test data")
    f2.write_bytes(b"CLI hardlink test data")

    exit_code = main([str(tmp_path), "--hardlink", "--confirm", "--quiet"])
    assert exit_code == 0
    stat1 = f1.stat()
    stat2 = f2.stat()
    assert stat1.st_ino == stat2.st_ino


def test_cli_symlink_with_confirm(tmp_path: Path, capsys):
    f1 = tmp_path / "a.dat"
    f2 = tmp_path / "b.dat"
    f1.write_bytes(b"CLI symlink test data")
    f2.write_bytes(b"CLI symlink test data")

    exit_code = main([str(tmp_path), "--symlink", "--confirm", "--quiet"])
    assert exit_code == 0
    assert f2.is_symlink()


def test_cli_delete_with_confirm(tmp_path: Path, capsys):
    f1 = tmp_path / "a.dat"
    f2 = tmp_path / "b.dat"
    f1.write_bytes(b"CLI delete test data")
    f2.write_bytes(b"CLI delete test data")

    exit_code = main([str(tmp_path), "--delete", "--confirm", "--quiet"])
    assert exit_code == 0
    assert f1.exists()
    assert not f2.exists()


def test_cli_interactive_cancel(tmp_path: Path, monkeypatch, capsys):
    f1 = tmp_path / "a.dat"
    f2 = tmp_path / "b.dat"
    f1.write_bytes(b"CLI cancel test data")
    f2.write_bytes(b"CLI cancel test data")

    monkeypatch.setattr("builtins.input", lambda _: "n")
    exit_code = main([str(tmp_path), "--delete", "--quiet"])
    assert exit_code == 0
    assert f1.exists()
    assert f2.exists()


def test_cli_invalid_size_arg(capsys):
    exit_code = main(["/tmp", "--min-size", "bad_value"])
    assert exit_code == 1
