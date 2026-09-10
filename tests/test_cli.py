# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive CLI tests for all subcommands and edge cases.
"""

from pathlib import Path

from lexicast_engine.cli import main, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "lexicast" in captured.out


def test_cli_ingest_and_list(tmp_path: Path, capsys):
    db_file = tmp_path / "cli_test.db"
    txt_file = tmp_path / "ep1.txt"
    txt_file.write_text("Long form discussion on neural networks and intelligence.", encoding="utf-8")

    # Ingest without distill
    exit_code = main(["--db", str(db_file), "ingest", str(txt_file), "--speaker", "Geoffrey Hinton"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Ingested" in captured.out

    # List
    exit_code = main(["--db", str(db_file), "list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Geoffrey Hinton" in captured.out
    assert "○ Raw" in captured.out


def test_cli_distill_subcommand(tmp_path: Path, capsys):
    db_file = tmp_path / "distill_test.db"
    txt_file = tmp_path / "ep.txt"
    txt_file.write_text("Discipline in first principles thinking. Focus on compounding.", encoding="utf-8")

    main(["--db", str(db_file), "ingest", str(txt_file), "--title", "Discipline & Principles"])
    capsys.readouterr()  # clear buffer

    # List to get ID
    main(["--db", str(db_file), "list"])
    captured = capsys.readouterr()
    ep_id = captured.out.split("[")[1].split("]")[0]

    # Explicit distill command
    exit_code = main(["--db", str(db_file), "distill", ep_id])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Distillation complete" in captured.out


def test_cli_search_and_export(tmp_path: Path, capsys):
    db_file = tmp_path / "cli_test2.db"
    txt_file = tmp_path / "ep2.txt"
    txt_file.write_text("Understanding stoicism and emotional resilience under extreme pressure.", encoding="utf-8")

    main(["--db", str(db_file), "ingest", str(txt_file), "--title", "Stoic Mindset", "--speaker", "Marcus", "--distill"])

    # Search match
    exit_code = main(["--db", str(db_file), "search", "resilience"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Stoic Mindset" in captured.out

    # Search no match
    exit_code = main(["--db", str(db_file), "search", "nonexistent_word_xyz"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "No matching" in captured.out

    # Get ep_id
    main(["--db", str(db_file), "list"])
    captured = capsys.readouterr()
    ep_id = captured.out.split("[")[1].split("]")[0]

    # Brief
    exit_code = main(["--db", str(db_file), "brief", ep_id])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "STOIC MINDSET" in captured.out

    # Export to stdout (json & md)
    exit_code = main(["--db", str(db_file), "export", ep_id, "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert '"Stoic Mindset"' in captured.out

    exit_code = main(["--db", str(db_file), "export", ep_id, "--format", "md"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "# 🎙️ Stoic Mindset" in captured.out

    # Export to files
    out_json = tmp_path / "exported.json"
    exit_code = main(["--db", str(db_file), "export", ep_id, "--format", "json", "--out", str(out_json)])
    assert exit_code == 0
    assert out_json.exists()

    out_md = tmp_path / "exported.md"
    exit_code = main(["--db", str(db_file), "export", ep_id, "--format", "md", "--out", str(out_md)])
    assert exit_code == 0
    assert out_md.exists()


def test_cli_error_paths(tmp_path: Path, capsys):
    db_file = tmp_path / "err.db"

    # List on empty db
    exit_code = main(["--db", str(db_file), "list"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "No episodes in database" in captured.out

    # Distill missing
    exit_code = main(["--db", str(db_file), "distill", "missing_id"])
    assert exit_code == 1

    # Brief missing
    exit_code = main(["--db", str(db_file), "brief", "missing_id"])
    assert exit_code == 1

    # Export missing
    exit_code = main(["--db", str(db_file), "export", "missing_id"])
    assert exit_code == 1

    # Ingest missing file
    exit_code = main(["--db", str(db_file), "ingest", "/nonexistent/path.txt"])
    assert exit_code == 1
