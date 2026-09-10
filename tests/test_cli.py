# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive CLI tests for oncorenal-core.
"""

from pathlib import Path

from oncorenal.cli import main, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "oncorenal" in captured.out


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"

    # Init
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "init",
            "--name",
            "George Vance",
            "--relationship",
            "Father",
            "--cancer-dx",
            "Colorectal Cancer Stage III",
            "--renal-dx",
            "ESRD on Hemodialysis",
            "--dry-weight",
            "70.0",
            "--fluid-limit",
            "1000.0",
        ]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Initialized Onco-Renal Profile" in captured.out

    # Add Chemo Cycle
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "chemo",
            "add",
            "--regimen",
            "FOLFOX",
            "--cycle",
            "1",
            "--total",
            "6",
            "--length",
            "14",
            "--nadir-start",
            "5",
            "--nadir-end",
            "10",
        ]
    )
    assert code == 0

    # List Chemo
    code = main(["--data-dir", str(data_dir), "chemo", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "FOLFOX" in captured.out

    # Nadir Monitor
    code = main(["--data-dir", str(data_dir), "chemo", "nadir"])
    assert code == 0
    captured = capsys.readouterr()
    assert "CHEMOTHERAPY NADIR IMMUNE MONITOR" in captured.out

    # Log Toxicity
    code = main(
        ["--data-dir", str(data_dir), "chemo", "log-tox", "--temp", "98.7", "--nausea", "1", "--neuropathy", "2"]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Logged Toxicity" in captured.out

    # Dialysis Session
    code = main(
        ["--data-dir", str(data_dir), "dialysis", "session", "--pre-wt", "72.4", "--post-wt", "70.1", "--uf", "2.3"]
    )
    assert code == 0

    # Dialysis List
    code = main(["--data-dir", str(data_dir), "dialysis", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "72.4kg" in captured.out

    # Dialysis IDWG
    code = main(["--data-dir", str(data_dir), "dialysis", "idwg"])
    assert code == 0
    captured = capsys.readouterr()
    assert "INTERDIALYTIC WEIGHT GAIN" in captured.out
    assert "Target Dry Weight" in captured.out

    # Fluid Log
    code = main(
        ["--data-dir", str(data_dir), "fluid", "log", "--ml", "850.0", "--potassium", "1500", "--phosphorus", "750"]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert "Logged Fluid" in captured.out

    # Fluid List
    code = main(["--data-dir", str(data_dir), "fluid", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "850 mL" in captured.out

    # Labs Add
    code = main(
        [
            "--data-dir",
            str(data_dir),
            "labs",
            "add",
            "--wbc",
            "4.5",
            "--anc",
            "1800",
            "--potassium",
            "4.9",
            "--phosphorus",
            "4.2",
            "--albumin",
            "4.1",
        ]
    )
    assert code == 0

    # Labs List
    code = main(["--data-dir", str(data_dir), "labs", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "4.9" in captured.out
    assert "mEq/L" in captured.out

    # Ask
    code = main(["--data-dir", str(data_dir), "ask", "What are the rules for managing fluids and chemo nadir?"])
    assert code == 0
    captured = capsys.readouterr()
    assert "AI ONCOLOGY & RENAL SPECIALTY COMPANION" in captured.out

    # Ask JSON
    code = main(["--data-dir", str(data_dir), "ask", "What is the dry weight status?", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"clinical_summary"' in captured.out
