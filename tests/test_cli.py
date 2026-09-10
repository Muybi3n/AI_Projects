# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Comprehensive CLI tests for medcadence-core.
"""

from pathlib import Path

from medcadence.cli import main, print_banner


def test_print_banner(capsys):
    print_banner()
    captured = capsys.readouterr()
    assert "medcadence" in captured.out


def test_cli_full_workflow(tmp_path: Path, capsys):
    data_dir = tmp_path / "data"

    # Init
    code = main(["--data-dir", str(data_dir), "init", "--label", "Jane Doe", "--sex", "female", "--birth-year", "1992"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Initialized Health Profile" in captured.out

    # Add Lab
    code = main(["--data-dir", str(data_dir), "lab", "add", "--name", "LDL Cholesterol", "--value", "135", "--high", "100", "--unit", "mg/dL"])
    assert code == 0

    # List Labs
    code = main(["--data-dir", str(data_dir), "lab", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "LDL Cholesterol" in captured.out

    # Lab Trends
    code = main(["--data-dir", str(data_dir), "lab", "trends"])
    assert code == 0
    captured = capsys.readouterr()
    assert "LONGITUDINAL BIOMARKER TRENDS" in captured.out

    # Lab Trends JSON
    code = main(["--data-dir", str(data_dir), "lab", "trends", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"latest_value"' in captured.out

    # Add Meds
    code = main(["--data-dir", str(data_dir), "med", "add", "--name", "Atorvastatin", "--dosage", "20mg"])
    assert code == 0
    code = main(["--data-dir", str(data_dir), "med", "add", "--name", "Grapefruit Juice", "--supplement"])
    assert code == 0

    # List Meds
    code = main(["--data-dir", str(data_dir), "med", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "Atorvastatin" in captured.out

    # Med Audit
    code = main(["--data-dir", str(data_dir), "med", "audit"])
    assert code == 0
    captured = capsys.readouterr()
    assert "SEVERE" in captured.out
    assert "CYP3A4" in captured.out

    # Med Audit JSON
    code = main(["--data-dir", str(data_dir), "med", "audit", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"item_a"' in captured.out

    # Telemetry
    code = main(["--data-dir", str(data_dir), "telemetry", "add", "--rhr", "54", "--hrv", "65", "--sleep-hours", "7.8"])
    assert code == 0

    code = main(["--data-dir", str(data_dir), "telemetry", "list"])
    assert code == 0
    captured = capsys.readouterr()
    assert "54.0 bpm" in captured.out

    # Emergency Card
    code = main(["--data-dir", str(data_dir), "emergency", "set", "--blood-type", "A+", "--allergies", "Penicillin", "--contacts", "Dr. House: 555-0199"])
    assert code == 0

    code = main(["--data-dir", str(data_dir), "emergency", "show"])
    assert code == 0
    captured = capsys.readouterr()
    assert "A+" in captured.out
    assert "Penicillin" in captured.out

    # Ask
    code = main(["--data-dir", str(data_dir), "ask", "What should I ask my doctor?"])
    assert code == 0
    captured = capsys.readouterr()
    assert "AI HEALTHCARE COMPANION" in captured.out

    # Ask JSON
    code = main(["--data-dir", str(data_dir), "ask", "Are my meds safe?", "--json"])
    assert code == 0
    captured = capsys.readouterr()
    assert '"clinical_synthesis"' in captured.out
