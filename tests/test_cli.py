# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
CLI tests for ptomax-core.
"""

from pathlib import Path

from ptomax.cli import main, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "PTOMAX" in captured.out


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"

    # Balance
    code = main(["--data-dir", str(data_dir), "balance"])
    assert code == 0
    captured = capsys.readouterr()
    assert "PTO BALANCE & ACCRUAL" in captured.out

    # Set Balance
    code = main(
        ["--data-dir", str(data_dir), "set-balance", "--balance", "18.0", "--allowance", "20.0"]
    )
    assert code == 0

    # Optimize
    code = main(["--data-dir", str(data_dir), "optimize", "--days", "15", "--year", "2026"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Optimized Holiday Stacking Schedule" in captured.out

    # Coverage List
    code = main(["--data-dir", str(data_dir), "coverage", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "PRE-VACATION WORK HANDOVER MATRIX" in captured.out

    # Coverage Add
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "coverage",
            "add",
            "--project",
            "Core API Gateway",
            "--primary-name",
            "Dana Scully",
            "--primary-contact",
            "dana@corp.internal",
        ]
    )
    assert code == 0

    # Coverage Ready
    code = main(["--data-dir", str(data_dir), "coverage", "ready", "--id", "Core API Gateway"])
    assert code == 0

    # OOO
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "ooo",
            "--start",
            "2026-07-03",
            "--end",
            "2026-07-12",
            "--style",
            "external",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Out-of-Office Email" in captured.out

    # Accrual
    code = main(["--data-dir", str(data_dir), "accrual"])
    assert code == 0
    captured = capsys.readouterr()
    assert "PTO Accrual & Rollover Audit" in captured.out

    # Ask
    code = main(["--data-dir", str(data_dir), "ask", "How can I stack holidays in 2026?"])
    assert code == 0
    captured = capsys.readouterr()
    assert "PTOMAX STRATEGIST" in captured.out
